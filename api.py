"""
api.py
======
RTL-Gen AI Web API
Runs on port 8502 alongside Streamlit (8501).

Usage:
  python api.py

Test:
  curl -X POST http://localhost:8502/api/generate \
    -H "Content-Type: application/json" \
    -d '{"description": "8-bit adder", "clock_ns": 10}'
"""

import os
import logging
import asyncio
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict
from contextlib import asynccontextmanager

log = logging.getLogger(__name__)

# =====================================================
# INSTALL CHECK
# =====================================================
try:
    from fastapi import FastAPI, HTTPException, BackgroundTasks
    from fastapi.responses import (
        FileResponse, JSONResponse
    )
    from fastapi.middleware.cors import CORSMiddleware
    from pydantic import BaseModel, Field
    import uvicorn
except ImportError:
    import subprocess, sys
    subprocess.run([
        sys.executable, "-m", "pip", "install",
        "fastapi", "uvicorn[standard]",
        "--break-system-packages", "-q"
    ])
    from fastapi import FastAPI, HTTPException, BackgroundTasks
    from fastapi.responses import FileResponse, JSONResponse
    from fastapi.middleware.cors import CORSMiddleware
    from pydantic import BaseModel, Field
    import uvicorn


# =====================================================
# IN-MEMORY JOB STORE
# =====================================================
JOBS: Dict[str, dict] = {}


# =====================================================
# REQUEST/RESPONSE MODELS
# =====================================================
class GenerateRequest(BaseModel):
    description: str = Field(
        ...,
        min_length=5,
        max_length=500,
        example="8-bit synchronous adder with carry"
    )
    module_name: Optional[str] = Field(
        None,
        example="my_adder"
    )
    clock_ns: float = Field(
        10.0,
        ge=1.0,
        le=100.0,
        example=10.0
    )
    llm_provider: str = Field(
        "gemini",
        example="gemini"
    )


class JobStatus(BaseModel):
    job_id:        str
    status:        str
    description:   str
    created_at:    str
    completed_at:  Optional[str]
    progress:      Optional[float] = 0.0
    current_step:  Optional[str]   = "Queued"
    gds_size_kb:   Optional[float]
    tapeout_ready: Optional[bool]
    method_used:   Optional[str]
    download_url:  Optional[str]
    warning:       Optional[str]
    error:         Optional[str]


# =====================================================
# LIFESPAN (startup/shutdown)
# =====================================================
@asynccontextmanager
async def lifespan(app: FastAPI):
    log.info("RTL-Gen AI API starting...")
    yield
    log.info("RTL-Gen AI API stopped.")


# =====================================================
# APP
# =====================================================
app = FastAPI(
    title="RTL-Gen AI API",
    description=(
        "Natural language to GDSII silicon layout. "
        "POST a circuit description, get a GDS file."
    ),
    version="1.4.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# =====================================================
# BACKGROUND PIPELINE RUNNER
# =====================================================
def run_pipeline_job(
    job_id: str,
    description: str,
    module_name: str,
    clock_ns: float,
    llm_provider: str
):
    """
    Run the full RTL-to-GDSII pipeline in background.
    Updates JOBS dict with progress.
    """
    JOBS[job_id]["status"]       = "running"
    JOBS[job_id]["progress"]     = 0.0
    JOBS[job_id]["current_step"] = "Starting..."
    log.info(f"Job {job_id}: starting pipeline")

    try:
        from guaranteed_flow import generate_guaranteed_gds
        JOBS[job_id]["current_step"] = "Generating Verilog..."
        JOBS[job_id]["progress"]     = 0.1

        result = generate_guaranteed_gds(
            description=description,
            module_name=module_name,
            llm_provider=llm_provider
        )

        JOBS[job_id].update({
            "status":        "complete",
            "progress":      1.0,
            "current_step":  "Done",
            "completed_at":  datetime.now().isoformat(),
            "gds_size_kb":   result["gds_size_kb"],
            "tapeout_ready": result["tapeout_ready"],
            "method_used":   result["method_used"],
            "gds_path":      result["gds_path"],
            "download_url":  f"/api/download/{job_id}",
            "error":         None
        })
        log.info(
            f"Job {job_id}: complete "
            f"({result['gds_size_kb']}KB)"
        )

    except Exception as e:
        JOBS[job_id].update({
            "status":       "failed",
            "progress":     0.0,
            "current_step": f"Failed: {str(e)[:100]}",
            "completed_at": datetime.now().isoformat(),
            "error":        str(e)
        })
        log.error(f"Job {job_id}: failed - {e}")


# =====================================================
# ENDPOINTS
# =====================================================
@app.get("/")
def root():
    return {
        "name":    "RTL-Gen AI API",
        "version": "1.4.0",
        "docs":    "/docs",
        "endpoints": {
            "generate": "POST /api/generate",
            "status":   "GET  /api/status/{job_id}",
            "download": "GET  /api/download/{job_id}",
            "jobs":     "GET  /api/jobs",
            "health":   "GET  /api/health"
        }
    }


@app.get("/api/health")
def health():
    """Health check endpoint."""
    from database import DB_AVAILABLE
    return {
        "status":     "healthy",
        "db":         DB_AVAILABLE,
        "jobs_total": len(JOBS),
        "jobs_running": sum(
            1 for j in JOBS.values()
            if j["status"] == "running"
        )
    }


@app.post("/api/generate",
          response_model=JobStatus,
          status_code=202)
def generate(
    request: GenerateRequest,
    background_tasks: BackgroundTasks
):
    """
    Submit a design generation job.

    Returns immediately with job_id.
    Poll /api/status/{job_id} for progress.
    Download from /api/download/{job_id} when complete.

    Example:
      POST /api/generate
      {"description": "4-bit counter with enable",
       "clock_ns": 10}
    """
    if not request.module_name:
        ts = datetime.now().strftime("%H%M%S")
        words = request.description.split()[:2]
        name_base = "_".join(
            w.lower() for w in words
            if w.isalpha()
        )
        module_name = f"{name_base}_{ts}" if name_base \
                      else f"design_{ts}"
    else:
        module_name = request.module_name

    job_id = f"job_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')[:20]}"
    JOBS[job_id] = {
        "job_id":       job_id,
        "status":       "queued",
        "description":  request.description,
        "module_name":  module_name,
        "clock_ns":     request.clock_ns,
        "created_at":   datetime.now().isoformat(),
        "completed_at": None,
        "gds_size_kb":  None,
        "tapeout_ready": None,
        "method_used":  None,
        "gds_path":     None,
        "download_url": None,
        "error":        None
    }

    background_tasks.add_task(
        run_pipeline_job,
        job_id,
        request.description,
        module_name,
        request.clock_ns,
        request.llm_provider
    )

    log.info(
        f"Job queued: {job_id} - {request.description[:50]}"
    )
    return JOBS[job_id]


@app.get("/api/status/{job_id}",
         response_model=JobStatus)
def get_status(job_id: str):
    """
    Check job status.

    Status values:
      queued   - waiting to start
      running  - pipeline executing
      complete - GDS ready for download
      failed   - error occurred
    """
    if job_id not in JOBS:
        raise HTTPException(
            status_code=404,
            detail=f"Job {job_id} not found"
        )
    return JOBS[job_id]


@app.get("/api/download/{job_id}")
def download_gds(job_id: str):
    """
    Download GDS file for completed job.
    Returns binary GDSII file.
    """
    if job_id not in JOBS:
        raise HTTPException(404, "Job not found")

    job = JOBS[job_id]

    if job["status"] != "complete":
        raise HTTPException(
            400,
            f"Job not complete. Status: {job['status']}"
        )

    gds_path = job.get("gds_path")
    if not gds_path or not Path(gds_path).exists():
        raise HTTPException(404, "GDS file not found")

    gds_file = Path(gds_path)
    if gds_file.stat().st_size < 100:
        raise HTTPException(
            500, "GDS file is too small (stub)"
        )

    return FileResponse(
        path=str(gds_file),
        filename=gds_file.name,
        media_type="application/octet-stream",
        headers={
            "X-GDS-Size-KB": str(job["gds_size_kb"]),
            "X-Tapeout-Ready": str(job["tapeout_ready"]),
            "X-Method-Used": str(job["method_used"]),
        }
    )


@app.get("/api/jobs")
def list_jobs(limit: int = 10):
    """List recent jobs."""
    recent = sorted(
        JOBS.values(),
        key=lambda x: x["created_at"],
        reverse=True
    )[:limit]
    return {
        "total": len(JOBS),
        "showing": len(recent),
        "jobs": recent
    }


@app.delete("/api/jobs/{job_id}")
def delete_job(job_id: str):
    """Delete a job from memory."""
    if job_id not in JOBS:
        raise HTTPException(404, "Job not found")
    del JOBS[job_id]
    return {"deleted": job_id}


# =====================================================
# RUN SERVER
# =====================================================
if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s: %(message)s"
    )
    print("RTL-Gen AI API")
    print("=" * 40)
    print("API Docs: http://localhost:8502/docs")
    print("Health:   http://localhost:8502/api/health")
    print()
    uvicorn.run(
        "api:app",
        host="0.0.0.0",
        port=8502,
        reload=False,
        log_level="info"
    )
