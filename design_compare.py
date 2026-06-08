"""
design_compare.py — Design Comparison Engine
RTL-Gen AI Phase 10

Compares two design runs (e.g. before/after optimization) and shows:
  - Fmax delta
  - Area delta
  - Power delta
  - Congestion delta
  - DRC delta
  - LVS delta
  - Cell count delta
  - Timing degradation

Useful for:
  - Optimization tracking (did my ECO help?)
  - PDK version comparison
  - Tool version comparison
  - Floorplan strategy comparison
"""

from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Dict, List, Optional, Any

log = logging.getLogger(__name__)


@dataclass
class DesignSnapshot:
    label: str = ""
    fmax_mhz: Optional[float] = None
    core_area_um2: Optional[float] = None
    utilization_pct: Optional[float] = None
    total_power_mw: Optional[float] = None
    dynamic_power_mw: Optional[float] = None
    leakage_uw: Optional[float] = None
    cell_count: Optional[int] = None
    setup_slack_ns: Optional[float] = None
    hold_slack_ns: Optional[float] = None
    drc_violations: Optional[int] = None
    lvs_status: str = "NOT_RUN"
    congestion_overflow_pct: Optional[float] = None
    gds_size_kb: Optional[float] = None
    timing_degradation_ns: Optional[float] = None
    tapeout_ready: bool = False

    @classmethod
    def from_design_db(cls, db, label: str = "") -> DesignSnapshot:
        """Create snapshot from DesignDB instance."""
        s = cls(label=label)
        if db.timing:
            s.fmax_mhz = db.timing.fmax_mhz
            s.hold_slack_ns = db.timing.hold_slack_ns
            tt = db.timing.corners.get("TT")
            if tt:
                s.setup_slack_ns = tt.slack_ns
        if db.power:
            s.total_power_mw = db.power.total_mw
            s.dynamic_power_mw = db.power.dynamic_mw
            s.leakage_uw = db.power.leakage_uw
        if db.congestion:
            s.congestion_overflow_pct = db.congestion.h_overflow_pct
        if db.drc:
            s.drc_violations = db.drc.violations
        if db.lvs:
            s.lvs_status = db.lvs.status
        if db.layout:
            s.core_area_um2 = db.layout.area_um2
        if db.placement:
            s.cell_count = db.placement.total_cells
        if db.signoff:
            s.tapeout_ready = all([
                db.signoff.timing_met, db.signoff.drc_clean,
                db.signoff.lvs_matched, db.signoff.gds_valid,
            ])
        return s

    @classmethod
    def from_results_dir(cls, results_dir: str, label: str = "") -> DesignSnapshot:
        """Create snapshot by parsing reports from a results directory."""
        s = cls(label=label)
        rd = Path(results_dir)

        # Timing
        sta = rd / "sta_final.txt"
        if sta.exists():
            text = sta.read_text(errors="ignore")
            m = re.search(r"slack\s+\((?:MET|VIOLATED)\)\s+([-\d.]+)", text)
            if m:
                s.setup_slack_ns = float(m.group(1))
            m = re.search(r"fmax_mhz\s*:\s*([\d.]+)", text, re.IGNORECASE)
            if m:
                s.fmax_mhz = float(m.group(1))

        # Power + Area
        pwr = rd / "power_report.txt"
        if pwr.exists():
            text = pwr.read_text(errors="ignore")
            m = re.search(
                r"Total\s+([\d.eE+-]+)\s+([\d.eE+-]+)\s+([\d.eE+-]+)\s+([\d.eE+-]+)", text
            )
            if m:
                s.total_power_mw = round(float(m.group(4)) * 1000, 4)
                s.dynamic_power_mw = round((float(m.group(1)) + float(m.group(2))) * 1000, 4)
                s.leakage_uw = round(float(m.group(3)) * 1e6, 4)

            # Area
            m = re.search(r"Design area\s+([\d.]+)\s+u\^2\s+([\d.]+)%", text)
            if m:
                s.core_area_um2 = float(m.group(1))
                s.utilization_pct = float(m.group(2))

        # DRC
        drc = rd / "drc_report.txt"
        if drc.exists():
            text = drc.read_text(errors="ignore")
            m = re.search(r"DRC\s+violations?\s*:\s*(\d+)", text, re.IGNORECASE)
            if m:
                s.drc_violations = int(m.group(1))

        # LVS
        lvs = rd / "lvs_report_final.txt"
        if lvs.exists():
            text = lvs.read_text(errors="ignore")
            if "circuits match uniquely" in text.lower() or "are equivalent" in text.lower():
                s.lvs_status = "MATCHED"
            elif "netlists do not match" in text.lower():
                s.lvs_status = "UNMATCHED"

        # Cell count from netlist
        nl = rd / f"{rd.parent.name}_sky130.v"
        if not nl.exists():
            nl = rd / "adder_8bit_sky130.v"
        if nl.exists():
            s.cell_count = len(re.findall(r"sky130_fd_sc_hd__", nl.read_text(errors="ignore")))

        # GDS
        gds = rd / f"{rd.parent.name}.gds"
        if not gds.exists():
            gds = rd / "adder_8bit.gds"
        if gds.exists():
            s.gds_size_kb = round(gds.stat().st_size / 1024, 1)

        return s

    def to_dict(self) -> Dict[str, Any]:
        return {k: v for k, v in asdict(self).items()}


@dataclass
class ComparisonResult:
    run_a: Optional[DesignSnapshot] = None
    run_b: Optional[DesignSnapshot] = None
    deltas: Dict[str, Any] = field(default_factory=dict)
    summary: str = ""


def compare_design_snapshots(
    run_a: DesignSnapshot,
    run_b: DesignSnapshot,
) -> ComparisonResult:
    """
    Compare two design snapshots and compute deltas.
    Positive delta = improvement (run_b better than run_a).

    Returns ComparisonResult with:
      - deltas: dict of metric -> delta value
      - summary: human-readable comparison
    """
    result = ComparisonResult(run_a=run_a, run_b=run_b)

    def _delta(a, b):
        if a is not None and b is not None:
            return round(b - a, 4)
        return None

    result.deltas = {
        "fmax_mhz": _delta(run_a.fmax_mhz, run_b.fmax_mhz),
        "core_area_um2": _delta(run_a.core_area_um2, run_b.core_area_um2),
        "utilization_pct": _delta(run_a.utilization_pct, run_b.utilization_pct),
        "total_power_mw": _delta(run_a.total_power_mw, run_b.total_power_mw),
        "dynamic_power_mw": _delta(run_a.dynamic_power_mw, run_b.dynamic_power_mw),
        "leakage_uw": _delta(run_a.leakage_uw, run_b.leakage_uw),
        "cell_count": _delta(run_a.cell_count, run_b.cell_count),
        "setup_slack_ns": _delta(run_a.setup_slack_ns, run_b.setup_slack_ns),
        "hold_slack_ns": _delta(run_a.hold_slack_ns, run_b.hold_slack_ns),
        "drc_violations": _delta(run_a.drc_violations, run_b.drc_violations),
        "congestion_overflow_pct": _delta(
            run_a.congestion_overflow_pct, run_b.congestion_overflow_pct
        ),
        "gds_size_kb": _delta(run_a.gds_size_kb, run_b.gds_size_kb),
        "timing_degradation_ns": _delta(
            run_a.timing_degradation_ns, run_b.timing_degradation_ns
        ),
    }

    # Build summary
    lines = [f"=== Design Comparison: {run_a.label} vs {run_b.label} ==="]
    improved = []
    degraded = []
    unchanged = []

    for metric, delta in result.deltas.items():
        if delta is None:
            continue
        a_val = getattr(run_a, metric, None)
        b_val = getattr(run_b, metric, None)

        # Determine if delta is improvement
        # For most metrics: positive = improvement
        # For area/power/drc/congestion: negative = improvement
        inverse_metrics = {
            "core_area_um2", "utilization_pct", "total_power_mw",
            "dynamic_power_mw", "leakage_uw", "drc_violations",
            "congestion_overflow_pct",
        }
        is_improvement = delta > 0 if metric not in inverse_metrics else delta < 0

        label = metric.replace("_", " ").title()
        if abs(delta) < 0.001:
            unchanged.append(f"  {label}: {a_val} (no change)")
        elif is_improvement:
            improved.append(f"  ✅ {label}: {a_val} -> {b_val} ({delta:+.4f})")
        else:
            degraded.append(f"  ❌ {label}: {a_val} -> {b_val} ({delta:+.4f})")

    if improved:
        lines.append("\n✅ Improvements:")
        lines.extend(improved)
    if degraded:
        lines.append("\n❌ Degradations:")
        lines.extend(degraded)
    if unchanged:
        lines.append("\n➡️ Unchanged:")
        lines.extend(unchanged)

    result.summary = "\n".join(lines)
    return result


def compare_design_runs(
    run_a_dir: str,
    run_b_dir: str,
    label_a: str = "Run A",
    label_b: str = "Run B",
) -> ComparisonResult:
    """
    Compare two run directories directly.
    Parses reports from each directory and computes deltas.

    Usage:
        result = compare_design_runs(
            "results/v2.5",
            "results/v2.6",
            label_a="v2.5",
            label_b="v2.6",
        )
        print(result.summary)
    """
    snap_a = DesignSnapshot.from_results_dir(run_a_dir, label=label_a)
    snap_b = DesignSnapshot.from_results_dir(run_b_dir, label=label_b)
    return compare_design_snapshots(snap_a, snap_b)


# ── Standalone test ──────────────────────────────────────────────────────────

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    print("=" * 60)
    print("design_compare.py -- standalone self-test")
    print("=" * 60)

    passed = total = 0

    # Test 1: Snapshot comparison with deltas
    total += 1
    a = DesignSnapshot(
        label="v2.5",
        fmax_mhz=100.0,
        core_area_um2=2500.0,
        total_power_mw=15.0,
        cell_count=1000,
        setup_slack_ns=5.0,
        drc_violations=2,
        lvs_status="MATCHED",
    )
    b = DesignSnapshot(
        label="v2.6",
        fmax_mhz=133.0,
        core_area_um2=2400.0,
        total_power_mw=12.0,
        cell_count=950,
        setup_slack_ns=6.5,
        drc_violations=0,
        lvs_status="MATCHED",
    )

    result = compare_design_snapshots(a, b)
    assert result.deltas["fmax_mhz"] == 33.0
    assert result.deltas["core_area_um2"] == -100.0  # area decreased = improvement
    assert result.deltas["drc_violations"] == -2  # fewer violations = improvement
    assert "Improvements" in result.summary
    print(f"[PASS] Design comparison deltas: Fmax +{result.deltas['fmax_mhz']} MHz")
    passed += 1

    # Test 2: Degradation detection
    total += 1
    worse = DesignSnapshot(label="worse", fmax_mhz=80.0, drc_violations=5, lvs_status="UNMATCHED")
    better = DesignSnapshot(label="better", fmax_mhz=100.0, drc_violations=0, lvs_status="MATCHED")
    result2 = compare_design_snapshots(worse, better)
    assert "Degradations" not in result2.summary  # worse->better is all improvement
    print(f"[PASS] Degradation detection: opposite direction shows improvements")
    passed += 1

    # Test 3: From results dir (no real files = graceful handling)
    total += 1
    import tempfile
    with tempfile.TemporaryDirectory() as tmp:
        snap = DesignSnapshot.from_results_dir(tmp, label="empty")
        assert snap.fmax_mhz is None
        assert snap.drc_violations is None
        print(f"[PASS] Empty results dir: all fields None, no crash")
        passed += 1

    print()
    print("=" * 60)
    print(f"Results: {passed}/{total} passed")
    if passed == total:
        print("ALL TESTS PASSED -- design_compare.py ready for integration")
    print("=" * 60)
