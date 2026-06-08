"""
tapeout_score.py — Tapeout Readiness Score
RTL-Gen AI Phase 10

Evaluates design readiness for tapeout based on real sign-off criteria.
Returns 0-100 score with blockers, warnings, and recommendations.

Evaluation criteria:
  - DRC clean:      20 pts (fatal if failing)
  - LVS matched:    20 pts (fatal if failing)
  - Timing met:     20 pts (fatal if failing)
  - GDS generated:  10 pts
  - SPEF extracted: 10 pts
  - Congestion OK:  10 pts
  - Power OK:       5 pts
  - Hold clean:     5 pts
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Dict, List, Optional, Any

log = logging.getLogger(__name__)


@dataclass
class TapeoutScore:
    score: int = 0
    max_score: int = 100
    percentage: int = 0
    blockers: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    recommendations: List[str] = field(default_factory=list)
    category_scores: Dict[str, int] = field(default_factory=dict)
    tapeout_ready: bool = False


def evaluate_tapeout_readiness(
    design_name: str,
    results_dir: str,
    db=None,
    sta_summary=None,
    drc_summary=None,
    lvs_summary=None,
    power_summary=None,
    congestion_summary=None,
    gds_path: Optional[str] = None,
    spef_path: Optional[str] = None,
) -> TapeoutScore:
    """
    Evaluate tapeout readiness from all available sources.
    The score is computed from *real* report data only.

    Args:
        design_name: Design name
        results_dir: Path to run results
        db: Optional DesignDB instance
        sta_summary: Optional STASummary from parsers
        drc_summary: Optional DRCSummary from parsers
        lvs_summary: Optional LVSSummary from parsers
        power_summary: Optional PowerSummary from parsers
        congestion_summary: Optional CongestionSummary from parsers
        gds_path: Path to GDS file
        spef_path: Path to SPEF file

    Returns:
        TapeoutScore with detailed evaluation
    """
    ts = TapeoutScore()
    rd = Path(results_dir)

    # Helper: check file exists with minimum size
    def _check_file(path, min_size=100, name="file"):
        p = Path(path) if path else None
        if p and p.exists() and p.stat().st_size >= min_size:
            return True
        return False

    # ── DRC Clean (20 pts) ─────────────────────────────────────────────
    if drc_summary is not None:
        if drc_summary.clean:
            ts.score += 20
            ts.category_scores["drc"] = 20
        else:
            ts.blockers.append(f"DRC: {drc_summary.total_violations} violations")
            ts.category_scores["drc"] = 0
            ts.recommendations.append("Fix all DRC violations before tapeout")
    elif db and db.drc:
        if db.drc.violations == 0:
            ts.score += 20
            ts.category_scores["drc"] = 20
        else:
            ts.blockers.append(f"DRC: {db.drc.violations} violations")
            ts.category_scores["drc"] = 0
    else:
        drc_report = rd / "drc_report.txt"
        if drc_report.exists():
            try:
                from parsers.drc_parser import parse_drc_report
                ds = parse_drc_report(drc_report.read_text(errors="ignore"))
                if ds.clean:
                    ts.score += 20
                    ts.category_scores["drc"] = 20
                else:
                    ts.blockers.append(f"DRC: {ds.total_violations} violations")
                    ts.category_scores["drc"] = 0
            except ImportError:
                ts.blockers.append("DRC parser unavailable")
                ts.category_scores["drc"] = 0
        else:
            ts.blockers.append("DRC report not found")
            ts.category_scores["drc"] = 0

    # ── LVS Matched (20 pts) ───────────────────────────────────────────
    if lvs_summary is not None:
        if lvs_summary.matched:
            ts.score += 20
            ts.category_scores["lvs"] = 20
        else:
            ts.blockers.append(f"LVS: {lvs_summary.status}")
            ts.category_scores["lvs"] = 0
    elif db and db.lvs:
        if db.lvs.status in ("MATCHED", "MATCHED_WITH_WARNINGS"):
            ts.score += 20
            ts.category_scores["lvs"] = 20
        else:
            ts.blockers.append(f"LVS: {db.lvs.status}")
            ts.category_scores["lvs"] = 0
    else:
        lvs_report = rd / "lvs_report_final.txt"
        if lvs_report.exists():
            try:
                from parsers.lvs_parser import parse_lvs_report
                ls = parse_lvs_report(lvs_report.read_text(errors="ignore"))
                if ls.matched:
                    ts.score += 20
                    ts.category_scores["lvs"] = 20
                else:
                    ts.blockers.append(f"LVS: {ls.status}")
                    ts.category_scores["lvs"] = 0
            except ImportError:
                ts.blockers.append("LVS parser unavailable")
                ts.category_scores["lvs"] = 0
        else:
            ts.blockers.append("LVS report not found")
            ts.category_scores["lvs"] = 0

    # ── Timing Met (20 pts) ────────────────────────────────────────────
    if sta_summary is not None:
        tt = sta_summary.corners.get("TT")
        if tt and tt.met:
            ts.score += 20
            ts.category_scores["timing"] = 20
        elif tt:
            ts.blockers.append(f"Timing: slack={tt.slack_ns}ns (violated)")
            ts.category_scores["timing"] = 0
        else:
            ts.blockers.append("Timing: TT corner not available")
            ts.category_scores["timing"] = 0
    elif db and db.timing:
        all_met = all(c.met for c in db.timing.corners.values()) if db.timing.corners else False
        if all_met:
            ts.score += 20
            ts.category_scores["timing"] = 20
        else:
            for name, c in db.timing.corners.items():
                if not c.met:
                    ts.blockers.append(f"Timing: {name} corner violated (slack={c.slack_ns}ns)")
            ts.category_scores["timing"] = 0
    else:
        sta_report = rd / "sta_final.txt"
        if sta_report.exists():
            try:
                from parsers.sta_parser import parse_sta_corner
                sc = parse_sta_corner(sta_report.read_text(errors="ignore"), "TT")
                if sc.met:
                    ts.score += 20
                    ts.category_scores["timing"] = 20
                else:
                    ts.blockers.append(f"Timing: slack={sc.slack_ns}ns (violated)")
                    ts.category_scores["timing"] = 0
            except ImportError:
                ts.blockers.append("STA parser unavailable")
                ts.category_scores["timing"] = 0
        else:
            ts.blockers.append("STA report not found")
            ts.category_scores["timing"] = 0

    # ── GDS Generated (10 pts) ─────────────────────────────────────────
    if _check_file(gds_path, min_size=50000, name="GDS"):
        ts.score += 10
        ts.category_scores["gds"] = 10
    elif db and db.gds_file and _check_file(db.gds_file):
        ts.score += 10
        ts.category_scores["gds"] = 10
    else:
        gds = rd / f"{design_name}.gds"
        if gds.exists() and gds.stat().st_size >= 50000:
            ts.score += 10
            ts.category_scores["gds"] = 10
        else:
            ts.blockers.append("GDS file missing or too small")
            ts.category_scores["gds"] = 0

    # ── SPEF Extracted (10 pts) ────────────────────────────────────────
    if _check_file(spef_path, min_size=100, name="SPEF"):
        ts.score += 10
        ts.category_scores["spef"] = 10
    else:
        spef = rd / f"{design_name}.spef"
        if spef.exists() and spef.stat().st_size >= 100:
            ts.score += 10
            ts.category_scores["spef"] = 10
        else:
            ts.warnings.append("SPEF file missing; post-layout timing unverified")
            ts.category_scores["spef"] = 0

    # ── Congestion OK (10 pts) ─────────────────────────────────────────
    if congestion_summary is not None:
        if congestion_summary.available:
            overflow = congestion_summary.h_overflow_pct or congestion_summary.v_overflow_pct
            if overflow is not None and overflow < 5.0:
                ts.score += 10
                ts.category_scores["congestion"] = 10
            elif overflow is not None:
                ts.warnings.append(f"Congestion overflow: {overflow}% > 5%")
                ts.category_scores["congestion"] = 5
            else:
                ts.category_scores["congestion"] = 5
    else:
        cong_report = rd / "congestion_report.txt"
        if cong_report.exists():
            try:
                from parsers.congestion_parser import parse_congestion_report
                cs = parse_congestion_report(cong_report.read_text(errors="ignore"))
                if cs.available:
                    overflow = cs.h_overflow_pct or cs.v_overflow_pct
                    if overflow is not None and overflow < 5.0:
                        ts.score += 10
                        ts.category_scores["congestion"] = 10
                    elif overflow is not None:
                        ts.warnings.append(f"Congestion overflow: {overflow}% > 5%")
                        ts.category_scores["congestion"] = 5
                    else:
                        ts.category_scores["congestion"] = 5
                else:
                    ts.category_scores["congestion"] = 0
            except ImportError:
                ts.category_scores["congestion"] = 0

    # ── Power OK (5 pts) ───────────────────────────────────────────────
    if power_summary is not None and power_summary.total_power_mw is not None:
        ts.score += 5
        ts.category_scores["power"] = 5
    elif db and db.power and db.power.total_mw is not None:
        ts.score += 5
        ts.category_scores["power"] = 5
    else:
        power_report = rd / "power_report.txt"
        if power_report.exists():
            try:
                from parsers.power_parser import parse_power_report
                ps = parse_power_report(power_report.read_text(errors="ignore"))
                if ps.total_power_mw is not None:
                    ts.score += 5
                    ts.category_scores["power"] = 5
                else:
                    ts.category_scores["power"] = 0
            except ImportError:
                ts.category_scores["power"] = 0
        else:
            ts.category_scores["power"] = 0

    # ── Hold Clean (5 pts) ─────────────────────────────────────────────
    hold_report = rd / "hold_analysis.txt"
    if hold_report.exists():
        import re
        text = hold_report.read_text(errors="ignore")
        if "HOLD_CLEAN" in text or re.search(r"([\d.]+)\s+slack\s+\(MET\)", text):
            ts.score += 5
            ts.category_scores["hold"] = 5
        else:
            ts.warnings.append("Hold analysis shows violations")
            ts.category_scores["hold"] = 0
    else:
        ts.category_scores["hold"] = 0

    # Compute final score and status
    ts.percentage = round(ts.score / ts.max_score * 100)
    ts.tapeout_ready = (
        ts.category_scores.get("drc", 0) >= 20
        and ts.category_scores.get("lvs", 0) >= 20
        and ts.category_scores.get("timing", 0) >= 20
        and ts.category_scores.get("gds", 0) >= 10
    )

    if ts.tapeout_ready:
        ts.recommendations.append("Design is tapeout-ready. Proceed with mask generation.")
    else:
        if not ts.tapeout_ready:
            ts.recommendations.insert(0, "Resolve all blockers before tapeout.")

    return ts


def score_from_results_dir(design_name: str, results_dir: str) -> TapeoutScore:
    """Convenience: evaluate tapeout readiness directly from a results directory."""
    from parsers import collect_all_metrics
    am = collect_all_metrics(results_dir, design_name)
    return evaluate_tapeout_readiness(
        design_name=design_name,
        results_dir=results_dir,
        sta_summary=am.sta,
        drc_summary=am.drc,
        lvs_summary=am.lvs,
        power_summary=am.power,
        congestion_summary=am.congestion,
        gds_path=str(Path(results_dir) / f"{design_name}.gds"),
        spef_path=str(Path(results_dir) / f"{design_name}.spef"),
    )


# ── Standalone test ──────────────────────────────────────────────────────────

if __name__ == "__main__":
    import tempfile
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    print("=" * 60)
    print("tapeout_score.py -- standalone self-test")
    print("=" * 60)

    passed = total = 0

    # Test 1: Perfect score
    total += 1
    from parsers.sta_parser import STASummary, STACorner
    from parsers.drc_parser import DRCSummary
    from parsers.lvs_parser import LVSSummary
    from parsers.power_parser import PowerSummary
    from parsers.congestion_parser import CongestionSummary

    sta = STASummary()
    sta.corners["TT"] = STACorner(corner="TT", slack_ns=5.0, met=True)
    drc = DRCSummary(total_violations=0, clean=True)
    lvs = LVSSummary(status="MATCHED", matched=True)
    pwr = PowerSummary(total_power_mw=15.0, dynamic_power_mw=12.0)
    cong = CongestionSummary(h_overflow_pct=2.0, v_overflow_pct=1.5, available=True)

    with tempfile.TemporaryDirectory() as tmp:
        rd = Path(tmp)
        gds = rd / "test.gds"
        gds.write_bytes(b"\x00" * 60000)

        ts = evaluate_tapeout_readiness(
            design_name="test",
            results_dir=str(rd),
            sta_summary=sta, drc_summary=drc, lvs_summary=lvs,
            power_summary=pwr, congestion_summary=cong,
            gds_path=str(gds),
            spef_path=None,
        )
        assert ts.tapeout_ready
        assert ts.percentage >= 85
        print(f"[PASS] Tapeout ready: {ts.percentage}% (score={ts.score}/{ts.max_score})")
        passed += 1

    # Test 2: Failing design
    total += 1
    sta_fail = STASummary()
    sta_fail.corners["TT"] = STACorner(corner="TT", slack_ns=-0.5, met=False)
    drc_fail = DRCSummary(total_violations=5, clean=False)
    lvs_fail = LVSSummary(status="UNMATCHED", matched=False)

    ts2 = evaluate_tapeout_readiness(
        design_name="fail_design",
        results_dir=str(Path(tmp) / "nonexistent"),
        sta_summary=sta_fail, drc_summary=drc_fail, lvs_summary=lvs_fail,
        gds_path=None, spef_path=None,
    )
    assert not ts2.tapeout_ready
    assert len(ts2.blockers) >= 3
    assert ts2.category_scores.get("drc", 100) == 0
    print(f"[PASS] Failing design: {ts2.percentage}%, blockers={len(ts2.blockers)}")
    passed += 1

    print()
    print("=" * 60)
    print(f"Results: {passed}/{total} passed")
    if passed == total:
        print("ALL TESTS PASSED -- tapeout_score.py ready for integration")
    print("=" * 60)
