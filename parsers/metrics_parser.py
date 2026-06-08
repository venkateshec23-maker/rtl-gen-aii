"""
metrics_parser.py — Aggregate metrics collector.
Collects all parsed reports into a single AggregateMetrics object.
Serves as the single entry point for populating DesignDB from real reports.

Usage:
    am = collect_all_metrics(results_dir="/path/to/results")
    am.populate_design_db(db)
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Any

from .sta_parser import (
    parse_sta_report, parse_sta_corner, STASummary, convert_to_design_db_timing,
)
from .power_parser import parse_power_report, PowerSummary
from .congestion_parser import parse_congestion_report, CongestionSummary
from .drc_parser import parse_drc_report, DRCSummary
from .lvs_parser import parse_lvs_report, LVSSummary

log = logging.getLogger(__name__)


@dataclass
class AggregateMetrics:
    design_name: str = ""
    results_dir: str = ""

    sta: Optional[STASummary] = None
    power: Optional[PowerSummary] = None
    congestion: Optional[CongestionSummary] = None
    drc: Optional[DRCSummary] = None
    lvs: Optional[LVSSummary] = None

    preroute_sta: Optional[Any] = None
    postroute_sta: Optional[Any] = None
    signoff_sta: Optional[Any] = None

    cell_count: Optional[int] = None
    gds_size_kb: Optional[float] = None
    run_complete: bool = False

    def populate_design_db(self, db: Any) -> None:
        """Populate a DesignDB instance with all parsed metrics."""
        from design_db import (
            TimingData, PowerData, CongestionData, DRCCheck, LVSCheck,
            PlacementData, LayoutInfo, FloorplanData, RoutingData,
        )

        # Timing
        if self.sta:
            td = convert_to_design_db_timing(self.sta)
            db.timing = td

            # Post-route timing fields stored in mcmm for now
            if self.signoff_sta:
                sf = self.signoff_sta
                if sf.slack_ns is not None:
                    if not db.timing.corners:
                        from design_db import TimingCorner
                        db.timing.corners["SIGNOFF"] = TimingCorner(
                            corner="SIGNOFF", slack_ns=sf.slack_ns, met=sf.met
                        )

        # Power
        if self.power:
            db.power = PowerData(
                dynamic_mw=self.power.dynamic_power_mw,
                leakage_uw=self.power.static_power_mw,
                total_mw=self.power.total_power_mw,
            )

        # Congestion
        if self.congestion and self.congestion.available:
            cd = CongestionData(
                h_overflow_pct=self.congestion.h_overflow_pct,
                v_overflow_pct=self.congestion.v_overflow_pct,
                max_density_pct=self.congestion.max_density_pct,
                utilization_pct=self.congestion.utilization_pct,
                unrouted_nets=self.congestion.unrouted_nets,
            )
            cd.compute_score()
            db.congestion = cd

        # DRC
        if self.drc:
            db.drc = DRCCheck(
                violations=self.drc.total_violations,
                categories=self.drc.by_category,
                coordinates=self.drc.coordinates,
            )

        # LVS
        if self.lvs:
            db.lvs = LVSCheck(
                status=self.lvs.status,
                matched_nets=self.lvs.matched_nets,
                unmatched_nets=self.lvs.unmatched_nets,
                device_mismatches=self.lvs.device_mismatches,
            )

        # Placement / cell count
        if self.cell_count is not None:
            db.placement = PlacementData(total_cells=self.cell_count)

        # Layout
        gds_path = Path(self.results_dir) / f"{self.design_name}.gds"
        if gds_path.exists():
            db.layout = LayoutInfo(
                gds_path=str(gds_path),
                area_um2=self.power.core_area_um2 if self.power else None,
            )

        log.info("DesignDB populated from %d parsed reports",
                 sum(1 for r in [self.sta, self.power, self.congestion, self.drc, self.lvs] if r))

    def to_dict(self) -> Dict[str, Any]:
        """Convert to serializable dict."""
        return {
            "design_name": self.design_name,
            "results_dir": self.results_dir,
            "cell_count": self.cell_count,
            "gds_size_kb": self.gds_size_kb,
            "run_complete": self.run_complete,
            "sta_corners": {
                name: {"corner": c.corner, "wns_ns": c.wns_ns, "tns_ns": c.tns_ns,
                        "slack_ns": c.slack_ns, "met": c.met, "paths": len(c.paths)}
                for name, c in (self.sta.corners.items() if self.sta else {})
            } if self.sta else {},
            "power": {
                "total_mw": self.power.total_power_mw,
                "dynamic_mw": self.power.dynamic_power_mw,
                "leakage_uw": self.power.static_power_mw,
                "area_um2": self.power.core_area_um2,
                "util_pct": self.power.utilization_pct,
            } if self.power else {},
            "congestion": {
                "h_overflow_pct": self.congestion.h_overflow_pct,
                "v_overflow_pct": self.congestion.v_overflow_pct,
                "max_density_pct": self.congestion.max_density_pct,
            } if self.congestion else {},
            "drc": {
                "violations": self.drc.total_violations,
                "clean": self.drc.clean,
                "categories": self.drc.by_category,
            } if self.drc else {},
            "lvs": {
                "status": self.lvs.status,
                "matched": self.lvs.matched,
            } if self.lvs else {},
        }


def collect_all_metrics(
    results_dir: str,
    design_name: str = "adder_8bit",
    clock_period_ns: float = 10.0,
) -> AggregateMetrics:
    """
    Collect and parse all OpenROAD reports from a results directory.
    This is the single entry point for real OpenROAD report parsing.

    Args:
        results_dir: Path to run results directory.
        design_name: Name of the design.
        clock_period_ns: Clock period in ns.

    Returns:
        AggregateMetrics with all parsed report data.
    """
    rd = Path(results_dir)
    am = AggregateMetrics(design_name=design_name, results_dir=str(rd))

    # Import types needed for assignment (must be before first use to avoid UnboundLocalError)
    from .sta_parser import STASummary, STACorner, parse_sta_corner
    from .drc_parser import parse_klayout_drc

    # STA reports
    for report_name, corner_name in [
        ("sta_final.txt", "TT"),
        ("sta_ss.txt", "SS"),
        ("sta_ff.txt", "FF"),
    ]:
        report_path = rd / report_name
        if report_path.exists():
            text = report_path.read_text(errors="ignore")
            if text.strip():
                if am.sta is None:
                    am.sta = STASummary()
                if not am.sta.corners.get(corner_name):
                    am.sta.corners[corner_name] = parse_sta_corner(text, corner_name)

    if am.sta is None:
        am.sta = STASummary()

    # Pre-route STA (if exists)
    preroute = rd / "sta_preroute.txt"
    if preroute.exists():
        am.preroute_sta = parse_sta_corner(preroute.read_text(errors="ignore"), "PREROUTE")
        am.sta.preroute = am.preroute_sta

    # Post-route STA (post-routing, pre-SPEF)
    postroute = rd / "sta_postroute.txt"
    if postroute.exists():
        am.postroute_sta = parse_sta_corner(postroute.read_text(errors="ignore"), "POSTROUTE")
        am.sta.postroute = am.postroute_sta

    # Signoff STA (post-SPEF)
    signoff_report = rd / "sta_signoff.txt"
    if signoff_report.exists():
        am.signoff_sta = parse_sta_corner(signoff_report.read_text(errors="ignore"), "SIGNOFF")
        am.sta.signoff = am.signoff_sta

    # Compute timing degradation
    if am.sta.corners.get("TT") and am.signoff_sta:
        tt = am.sta.corners["TT"]
        sf = am.signoff_sta
        if tt.slack_ns is not None and sf.slack_ns is not None:
            am.sta.timing_degradation_ns = round(tt.slack_ns - sf.slack_ns, 4)

    # Power report
    power_report = rd / "power_report.txt"
    if power_report.exists():
        am.power = parse_power_report(power_report.read_text(errors="ignore"))

    # Congestion report
    congestion_report = rd / "congestion_report.txt"
    if congestion_report.exists():
        am.congestion = parse_congestion_report(congestion_report.read_text(errors="ignore"))

    # DRC reports
    drc_report = rd / "drc_report.txt"
    if drc_report.exists():
        am.drc = parse_drc_report(drc_report.read_text(errors="ignore"))
    else:
        klayout_drc = rd / "klayout_drc.xml"
        if klayout_drc.exists():
            am.drc = parse_klayout_drc(klayout_drc.read_text(errors="ignore"))

    # LVS report
    lvs_report = rd / "lvs_report_final.txt"
    if lvs_report.exists():
        am.lvs = parse_lvs_report(lvs_report.read_text(errors="ignore"))

    # Cell count from synthesis netlist
    nl_path = rd / f"{design_name}_sky130.v"
    if nl_path.exists():
        import re
        content = nl_path.read_text(errors="ignore")
        am.cell_count = len(re.findall(r"sky130_fd_sc_hd__", content))

    # GDS size
    gds_path = rd / f"{design_name}.gds"
    if gds_path.exists():
        am.gds_size_kb = round(gds_path.stat().st_size / 1024, 1)
        am.run_complete = True

    log.info("collect_all_metrics: %d reports parsed for %s",
             sum(1 for r in [am.sta and bool(am.sta.corners), am.power,
                             am.congestion, am.drc, am.lvs] if r),
             design_name)
    return am
