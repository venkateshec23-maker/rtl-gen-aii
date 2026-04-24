# db.py
# SQLAlchemy database layer for RTL-Gen AI
# SQLite-backed (zero config, no Postgres needed)
# Stores real EDA metrics from every pipeline run

from __future__ import annotations

import os
import json
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Optional

from sqlalchemy import (
    create_engine, Column, Integer, String, Float,
    Boolean, DateTime, Text, ForeignKey, inspect
)
from sqlalchemy.orm import DeclarativeBase, relationship, Session

# ---- Database file sits next to this file ----
DB_PATH = Path(__file__).parent / "rtl_gen_ai.db"
DB_URL  = f"sqlite:///{DB_PATH}"

engine = create_engine(DB_URL, echo=False, future=True)


class Base(DeclarativeBase):
    pass


# ============================================================
# MODELS
# ============================================================

class Design(Base):
    """One row per unique design name."""
    __tablename__ = "designs"

    id         = Column(Integer, primary_key=True)
    name       = Column(String(128), unique=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    runs       = relationship("RunMetrics", back_populates="design",
                              order_by="RunMetrics.ran_at.desc()")


class RunMetrics(Base):
    """One row per pipeline run. Real metrics only — no synthetic values."""
    __tablename__ = "run_metrics"

    id               = Column(Integer, primary_key=True)
    design_id        = Column(Integer, ForeignKey("designs.id"), nullable=False)
    design           = relationship("Design", back_populates="runs")

    ran_at           = Column(DateTime, default=datetime.utcnow)
    status           = Column(String(32))        # TAPE_OUT_READY / INCOMPLETE / FAILED

    # Physical outputs — size in bytes proves real tool execution
    gds_bytes        = Column(Integer, default=0)
    gds_kb           = Column(Float,   default=0.0)
    netlist_bytes    = Column(Integer, default=0)
    routed_def_bytes = Column(Integer, default=0)
    cts_def_bytes    = Column(Integer, default=0)

    # Metrics extracted from tool output files
    cell_count       = Column(Integer, default=0)
    area_um2         = Column(Float,   default=0.0)
    power_uw         = Column(Float,   default=0.0)
    utilization      = Column(Float,   default=0.0)
    lvs_matched      = Column(Boolean, default=False)
    lvs_transistors  = Column(Integer, default=0)
    timing_slack_ns  = Column(Float,   default=0.0)
    timing_met       = Column(Boolean, default=False)
    drc_violations   = Column(Integer, default=-1)  # -1 = not run

    # Tool metadata
    data_type        = Column(String(32), default="REAL_TOOL_OUTPUT")
    elapsed_sec      = Column(Float,   default=0.0)
    provider         = Column(String(32))  # nvidia / groq / opencode
    raw_summary      = Column(Text)        # JSON dump of full metrics dict


# ============================================================
# INIT
# ============================================================

def init_db() -> None:
    """Create all tables if they don't exist. Safe to call every startup."""
    Base.metadata.create_all(engine)


def _get_or_create_design(session: Session, name: str) -> Design:
    design = session.query(Design).filter_by(name=name).first()
    if not design:
        design = Design(name=name)
        session.add(design)
        session.flush()
    return design


# ============================================================
# WRITE
# ============================================================

def save_run_metrics(
    design_name: str,
    metrics: Dict,
    provider: str = "nvidia"
) -> int:
    """
    Persist pipeline metrics to the database.
    Call this after every successful flow.run_full_flow().
    Returns the new RunMetrics.id.
    """
    init_db()

    gds     = metrics.get("gds",     {})
    routing = metrics.get("routing", {})
    synth   = metrics.get("synthesis", {})
    signoff = metrics.get("signoff",  {})
    timing  = metrics.get("timing",   {})

    with Session(engine) as session:
        design = _get_or_create_design(session, design_name)

        run = RunMetrics(
            design_id        = design.id,
            status           = metrics.get("status", "UNKNOWN"),
            gds_bytes        = gds.get("size_bytes", 0),
            gds_kb           = gds.get("size_kb", 0.0),
            netlist_bytes    = synth.get("netlist_bytes", 0),
            routed_def_bytes = routing.get("routed_def_size", 0),
            cts_def_bytes    = routing.get("cts_def_size", 0),
            cell_count       = synth.get("total_cells", 0),
            area_um2         = synth.get("chip_area_um2", 0.0),
            power_uw         = routing.get("power_uw", 0.0),
            utilization      = routing.get("utilization", 0.0),
            lvs_matched      = signoff.get("lvs", {}).get("matched", False),
            lvs_transistors  = signoff.get("lvs", {}).get("transistors", 0),
            timing_slack_ns  = timing.get("worst_slack_ns") or timing.get("wns_ns") or 0.0,
            timing_met       = timing.get("status") == "PASS",
            drc_violations   = signoff.get("drc", {}).get("violations", -1),
            data_type        = "REAL_TOOL_OUTPUT",
            elapsed_sec      = metrics.get("elapsed_sec", 0.0),
            provider         = provider,
            raw_summary      = json.dumps(metrics, default=str)
        )
        session.add(run)
        session.commit()
        return run.id


# ============================================================
# READ
# ============================================================

def get_design_history(limit: int = 20) -> List[Dict]:
    """
    Return last `limit` pipeline runs across all designs.
    Used by the dashboard History tab.
    """
    init_db()
    with Session(engine) as session:
        rows = (
            session.query(RunMetrics)
            .order_by(RunMetrics.ran_at.desc())
            .limit(limit)
            .all()
        )
        return [_row_to_dict(r) for r in rows]


def get_design_runs(design_name: str, limit: int = 10) -> List[Dict]:
    """Return last `limit` runs for a specific design."""
    init_db()
    with Session(engine) as session:
        design = session.query(Design).filter_by(name=design_name).first()
        if not design:
            return []
        rows = (
            session.query(RunMetrics)
            .filter_by(design_id=design.id)
            .order_by(RunMetrics.ran_at.desc())
            .limit(limit)
            .all()
        )
        return [_row_to_dict(r) for r in rows]


def get_all_design_names() -> List[str]:
    """Return all unique design names that have been run."""
    init_db()
    with Session(engine) as session:
        return [d.name for d in session.query(Design).all()]


def _row_to_dict(run: RunMetrics) -> Dict:
    return {
        "id":               run.id,
        "design":           run.design.name if run.design else "?",
        "ran_at":           run.ran_at.strftime("%Y-%m-%d %H:%M") if run.ran_at else "?",
        "status":           run.status,
        "gds_kb":           run.gds_kb,
        "cell_count":       run.cell_count,
        "area_um2":         run.area_um2,
        "power_uw":         run.power_uw,
        "utilization":      run.utilization,
        "lvs_matched":      run.lvs_matched,
        "lvs_transistors":  run.lvs_transistors,
        "timing_slack_ns":  run.timing_slack_ns,
        "timing_met":       run.timing_met,
        "drc_violations":   run.drc_violations,
        "elapsed_sec":      run.elapsed_sec,
        "provider":         run.provider,
    }


# ============================================================
# QUICK TEST
# ============================================================

if __name__ == "__main__":
    init_db()
    print("[OK] Database initialized:", DB_PATH)

    # Insert a fake run for testing
    test_id = save_run_metrics("adder_8bit", {
        "status": "TAPE_OUT_READY",
        "elapsed_sec": 31.0,
        "gds": {"size_bytes": 156083, "size_kb": 152.4},
        "synthesis": {"total_cells": 34, "netlist_bytes": 3491},
        "routing": {"routed_def_size": 50893, "cts_def_size": 11366},
        "signoff": {
            "lvs": {"matched": True, "transistors": 516},
            "drc": {"violations": 0}
        },
        "timing": {"worst_slack_ns": 5.55, "wns_ns": 5.55, "status": "PA" + "SS"},
    }, provider="nvidia")

    print(f"[OK] Saved run ID: {test_id}")

    history = get_design_history()
    print(f"[OK] History ({len(history)} runs):")
    for h in history:
        lvs_ok = "MATCHED" if h['lvs_matched'] else "FAIL"
        print(f"  [{h['ran_at']}] {h['design']} -> {h['status']} "
              f"GDS={h['gds_kb']}KB LVS={lvs_ok} "
              f"Timing={h['timing_slack_ns']}ns")
