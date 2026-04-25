import threading
import queue
import time
import logging
from typing import Dict, List, Optional, Callable
from concurrent.futures import ThreadPoolExecutor

log = logging.getLogger(__name__)

# Safe database import — DB may not be available in all environments
try:
    from database import DB_AVAILABLE, save_run_metrics as _db_save_run_metrics
    def save_run_metrics(design_name, metrics, provider="unknown"):
        return _db_save_run_metrics(design_name, metrics, provider=provider)
except ImportError:
    DB_AVAILABLE = False
    def save_run_metrics(design_name, metrics, provider="unknown"):
        return False

# Safe RealMetricsParser import
try:
    from full_flow import RealMetricsParser
except ImportError:
    RealMetricsParser = None


class DesignTask:
    def __init__(self, design_name: str, verilog_file: str, provider: str = "gemini"):
        self.design_name = design_name
        self.verilog_file = verilog_file
        self.provider = provider
        self.status = "QUEUED"
        self.progress = 0
        self.steps = []
        self.result = None
        self.error = None
        self.start_time = None
        self.end_time = None

class DesignQueue:
    def __init__(self, max_parallel: int = 1):
        self.tasks: Dict[str, DesignTask] = {}
        self.queue = queue.Queue()
        self.max_parallel = max_parallel
        self.executor = ThreadPoolExecutor(max_workers=max_parallel)
        self._start_worker()

    def add_task(self, design_name: str, verilog_file: str, provider: str = "gemini") -> str:
        task_id = f"{design_name}_{int(time.time())}"
        task = DesignTask(design_name, verilog_file, provider)
        self.tasks[task_id] = task
        self.queue.put((task_id, task))
        return task_id

    def _start_worker(self):
        def worker():
            while True:
                task_id, task = self.queue.get()
                self._run_task(task_id, task)
                self.queue.task_done()
        
        t = threading.Thread(target=worker, daemon=True)
        t.start()

    def _run_task(self, task_id: str, task: DesignTask):
        from full_flow import RTLtoGDSIIFlow
        import os
        # DB_AVAILABLE and save_run_metrics imported at module level
        
        task.status = "RUNNING"
        task.start_time = time.time()
        
        def on_progress(step_name, step_num, total_steps, step_status):
            task.progress = int((step_num / total_steps) * 100)
            task.steps.append(f"{step_name}: {step_status}")

        try:
            work_dir = os.getenv("OPENLANE_WORK", r"C:\tools\OpenLane")
            pdk_dir = os.getenv("PDK_ROOT", r"C:\pdk")
            
            flow = RTLtoGDSIIFlow(
                design_name=task.design_name,
                verilog_file=task.verilog_file,
                work_dir=work_dir,
                pdk_dir=pdk_dir
            )
            
            task.result = flow.run_full_flow(progress_callback=on_progress)
            task.status = "COMPLETED" if task.result.get("tapeout_ready") else "FAILED"
            
            # Save to DB (use module-level RealMetricsParser import)
            if DB_AVAILABLE and RealMetricsParser is not None:
                parser = RealMetricsParser(task.result.get("results_dir"))
                save_run_metrics(task.design_name, parser.get_all_metrics(), provider=task.provider)
                
        except Exception as e:
            task.status = "ERROR"
            task.error = str(e)
            log.error(f"Task {task_id} failed: {e}")
        finally:
            task.end_time = time.time()

    def get_status(self, task_id: str) -> Optional[DesignTask]:
        return self.tasks.get(task_id)

    def list_tasks(self) -> List[Dict]:
        return [
            {
                "id": tid,
                "name": t.design_name,
                "status": t.status,
                "progress": t.progress,
                "error": t.error
            }
            for tid, t in self.tasks.items()
        ]
