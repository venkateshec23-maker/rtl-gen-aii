# database.py
# PostgreSQL integration for RTL-Gen AI
# Stores real pipeline run results
# Falls back to JSON when PostgreSQL is unavailable

import os
import json
import logging
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional

log = logging.getLogger(__name__)

DB_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://postgres:postgres@localhost:5432/rtlgenai"
)

_JSON_INDEX = Path(r"C:\tools\OpenLane\runs\index.json")


def get_connection():
    """Get PostgreSQL connection, or None if unavailable."""
    try:
        import psycopg2
        conn = psycopg2.connect(DB_URL)
        return conn
    except ImportError:
        try:
            import psycopg
            conn = psycopg.connect(DB_URL)
            return conn
        except ImportError:
            log.debug("No PostgreSQL driver installed — using JSON fallback")
            return None
        except Exception as e:
            log.debug(f"DB connection failed with psycopg: {e} — using JSON fallback")
            return None
    except Exception as e:
        log.debug(f"DB connection failed: {e} — using JSON fallback")
        return None


def _test_connection() -> bool:
    """Test DB connectivity at import time for DB_AVAILABLE flag."""
    conn = get_connection()
    if conn:
        conn.close()
        return True
    return False


# Exported flag: True if PostgreSQL is reachable, False = JSON fallback
DB_AVAILABLE: bool = _test_connection()

def init_database() -> bool:
    """Create tables if they don't exist. Returns True on success."""
    conn = get_connection()
    if not conn:
        # JSON index is zero-config; nothing to init
        _JSON_INDEX.parent.mkdir(parents=True, exist_ok=True)
        return False  # Signal that JSON fallback is active

    try:
        cur = conn.cursor()
        cur.execute("""
            CREATE TABLE IF NOT EXISTS design_runs (
                id              SERIAL PRIMARY KEY,
                run_id          VARCHAR(100) UNIQUE NOT NULL,
                design_name     VARCHAR(100) NOT NULL,
                description     TEXT,
                llm_provider    VARCHAR(50),
                status          VARCHAR(50),
                tapeout_ready   BOOLEAN DEFAULT FALSE,
                elapsed_sec     FLOAT,
                results_dir     TEXT,
                gds_path        TEXT,
                gds_size_bytes  INTEGER DEFAULT 0,
                cell_count      INTEGER DEFAULT 0,
                area_um2        FLOAT DEFAULT 0.0,
                power_uw        FLOAT DEFAULT 0.0,
                utilization     FLOAT DEFAULT 0.0,
                lvs_status      VARCHAR(20),
                timing_slack_ns FLOAT,
                drc_violations  INTEGER DEFAULT 0,
                transistors     INTEGER DEFAULT 0,
                created_at      TIMESTAMP DEFAULT NOW(),
                updated_at      TIMESTAMP DEFAULT NOW()
            );

            CREATE TABLE IF NOT EXISTS design_files (
                id          SERIAL PRIMARY KEY,
                run_id      VARCHAR(100) REFERENCES design_runs(run_id),
                file_type   VARCHAR(50),
                file_path   TEXT,
                file_size   INTEGER,
                created_at  TIMESTAMP DEFAULT NOW()
            );

            CREATE TABLE IF NOT EXISTS pipeline_steps (
                id           SERIAL PRIMARY KEY,
                run_id       VARCHAR(100) REFERENCES design_runs(run_id),
                step_name    VARCHAR(100),
                status       VARCHAR(20),
                duration_sec FLOAT,
                created_at   TIMESTAMP DEFAULT NOW()
            );
        """)
        conn.commit()
        cur.close()
        conn.close()
        log.info("PostgreSQL database initialized")
        return True
    except Exception as e:
        log.error(f"Database init failed: {e}")
        try:
            conn.close()
        except Exception:
            pass
        return False


def save_run(summary: Dict) -> bool:
    """Save pipeline run — PostgreSQL first, JSON fallback."""
    conn = get_connection()
    if not conn:
        return _save_run_json(summary)

    try:
        cur = conn.cursor()

        gds_path = summary.get("gds_path", "")
        gds_size = 0
        if gds_path and Path(gds_path).exists():
            gds_size = Path(gds_path).stat().st_size

        metrics = summary.get("metrics", {})
        synth   = metrics.get("synthesis", {})
        lvs     = metrics.get("signoff", {}).get("lvs", {})
        drc     = metrics.get("signoff", {}).get("drc", {})
        timing  = metrics.get("timing", {})

        if not gds_size:
            gds_size = int(metrics.get("gds", {}).get("size_bytes", 0) or 0)

        lvs_status = lvs.get("status")
        if not lvs_status:
            if lvs.get("matched") is True:
                lvs_status = "MATCHED"
            elif lvs.get("matched") is False:
                lvs_status = "UNMATCHED"

        if isinstance(lvs_status, str):
            status_map = {
                "MATCHED_WITH_WARNINGS": "MATCHED_WARN"
            }
            lvs_status = status_map.get(lvs_status, lvs_status)
            if len(lvs_status) > 20:
                lvs_status = lvs_status[:20]

        timing_slack = (
            timing.get("slack")
            if timing.get("slack") is not None else
            timing.get("worst_slack_ns")
            if timing.get("worst_slack_ns") is not None else
            timing.get("wns_ns", 0)
        )

        cur.execute("""
            INSERT INTO design_runs (
                run_id, design_name, status, tapeout_ready,
                elapsed_sec, results_dir, gds_path,
                gds_size_bytes, cell_count, area_um2, power_uw, utilization,
                lvs_status, timing_slack_ns, drc_violations
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (run_id) DO UPDATE SET
                status        = EXCLUDED.status,
                tapeout_ready = EXCLUDED.tapeout_ready,
                updated_at    = NOW()
        """, (
            summary.get("run_id", summary.get("design", summary.get("design_name"))),
            summary.get("design_name", summary.get("design")),
            summary.get("status"),
            summary.get("tapeout_ready", False),
            summary.get("elapsed_sec"),
            str(summary.get("results_dir", "")),
            gds_path,
            gds_size,
            synth.get("total_cells", 0),
            synth.get("chip_area_um2", 0.0),
            0.0, # placeholder for power
            0.0, # placeholder for utilization
            lvs_status,
            timing_slack,
            int(drc.get("violations", 0) or 0)
        ))

        for step, result in summary.get("steps", {}).items():
            cur.execute("""
                INSERT INTO pipeline_steps (run_id, step_name, status)
                VALUES (%s, %s, %s)
            """, (
                summary.get("run_id", summary.get("design")),
                step, result
            ))

        conn.commit()
        cur.close()
        conn.close()
        log.info(f"Run saved to PostgreSQL: {summary.get('run_id')}")
        return True

    except Exception as e:
        log.error(f"PostgreSQL save failed: {e} — falling back to JSON")
        try:
            conn.close()
        except Exception:
            pass
        return _save_run_json(summary)


def _save_run_json(summary: Dict) -> bool:
    """JSON fallback storage."""
    # Use WORK_DIR/runs/index.json or default path
    work_dir = os.getenv("OPENLANE_WORK", r"C:\tools\OpenLane")
    index_path = Path(work_dir) / "runs" / "index.json"
    index_path.parent.mkdir(parents=True, exist_ok=True)

    runs = []
    if index_path.exists():
        try:
            with open(index_path) as f:
                runs = json.load(f)
        except Exception:
            runs = []

    run_id = summary.get("run_id", summary.get("design", "unknown"))
    # Avoid duplicate run_ids
    runs = [r for r in runs if r.get("run_id") != run_id]
    runs.append({
        "run_id":        run_id,
        "design_name":   summary.get("design_name", summary.get("design")),
        "status":        summary.get("status"),
        "tapeout_ready": summary.get("tapeout_ready", False),
        "elapsed_sec":   summary.get("elapsed_sec"),
        "results_dir":   str(summary.get("results_dir", "")),
        "gds_path":      summary.get("gds_path", ""),
        "timestamp":     datetime.now().isoformat()
    })

    with open(index_path, 'w') as f:
        json.dump(runs, f, indent=2)

    log.info(f"Run saved to JSON index: {index_path}")
    return True


def get_all_runs() -> List[Dict]:
    """Get all design runs — PostgreSQL or JSON fallback."""
    conn = get_connection()
    if conn:
        try:
            cur = conn.cursor()
            cur.execute("""
                SELECT run_id, design_name, status, tapeout_ready,
                       elapsed_sec, gds_size_bytes, cell_count,
                       lvs_status, timing_slack_ns, results_dir,
                       gds_path, created_at, area_um2, power_uw, utilization
                FROM design_runs
                ORDER BY created_at DESC
            """)
            rows = cur.fetchall()
            cur.close()
            conn.close()
            return [
                {
                    "run_id":           r[0],
                    "design_name":      r[1],
                    "status":           r[2],
                    "tapeout_ready":    r[3],
                    "elapsed_sec":      r[4],
                    "gds_size_bytes":   r[5],
                    "cell_count":       r[6],
                    "lvs_status":       r[7],
                    "timing_slack_ns":  r[8],
                    "results_dir":      r[9],
                    "gds_path":         r[10],
                    "timestamp":        str(r[11]),
                    "area_um2":         r[12],
                    "power_uw":         r[13],
                    "utilization":      r[14]
                }
                for r in rows
            ]
        except Exception as e:
            log.error(f"PostgreSQL query failed: {e}")

    # JSON fallback
    work_dir   = os.getenv("OPENLANE_WORK", r"C:\tools\OpenLane")
    index_path = Path(work_dir) / "runs" / "index.json"
    if index_path.exists():
        try:
            with open(index_path) as f:
                return json.load(f)
        except Exception:
            pass
    return []


def get_db_status() -> Dict:
    """Check database connection status."""
    conn = get_connection()
    if conn:
        conn.close()
        return {
            "connected": True,
            "type":      "PostgreSQL",
            "url":       DB_URL
        }
    work_dir   = os.getenv("OPENLANE_WORK", r"C:\tools\OpenLane")
    index_path = Path(work_dir) / "runs" / "index.json"
    return {
        "connected": False,
        "type":      "JSON fallback",
        "path":      str(index_path)
    }
