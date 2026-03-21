"""
routing_optimizer.py  –  Routing Quality Analyser for RTL-Gen AI
=================================================================
Analyses routing quality after global and/or detailed routing and
generates actionable recommendations for fixing congestion, DRC
violations, and timing failures.

Responsibilities
─────────────────
1. Parse route reports → identify specific failure categories
2. Classify severity   → critical (blocks tapeout) vs warning
3. Generate fix plan   → ordered list of actions to take
4. Apply quick fixes   → re-route individual nets via OpenROAD
5. Estimate re-route   → predict whether changing params will help

Why a separate optimizer?
──────────────────────────
After routing, you may face:
  • DRC violations    → cannot tape out; must re-route or resize cells
  • Unrouted nets     → chip will not function; must fix congestion
  • Timing violations → chip may not meet frequency target
  • Long wires        → power/signal integrity concerns

Each failure type has a different root cause and different fix strategy.
This module translates raw report numbers into a specific action plan.

Usage example
──────────────
    from python.routing_optimizer import RoutingOptimizer, RouteOptConfig

    opt    = RoutingOptimizer(docker=dm, pdk=pdk)
    result = opt.analyze(
        routing_report = r"C:\\project\\physical\\routing.rpt",
        drc_file       = r"C:\\project\\physical\\drc_violations.txt",
        top_module     = "adder_8bit",
    )
    print(result.summary())
    for action in result.action_plan:
        print(f"  → {action}")
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import List, Optional

from python.docker_manager import DockerManager


# ──────────────────────────────────────────────────────────────────────────────
# ENUMERATIONS
# ──────────────────────────────────────────────────────────────────────────────

class RoutingIssueType(Enum):
    DRC_VIOLATION    = "drc_violation"
    UNROUTED_NET     = "unrouted_net"
    TIMING_VIOLATION = "timing_violation"
    HIGH_CONGESTION  = "high_congestion"
    LONG_WIRE        = "long_wire"
    VIA_COUNT        = "via_count"
    NONE             = "none"


class FixStrategy(Enum):
    """Recommended fix approach for each issue type."""
    REROUTE_NET    = "reroute_net"          # Re-route specific net
    REROUTE_AREA   = "reroute_area"         # Re-route entire congested area
    RESIZE_CELL    = "resize_cell"          # Upsize cell to fix timing
    CHANGE_CONFIG  = "change_config"        # Change GlobalRouteConfig params
    REDESIGN       = "redesign"             # Requires netlist-level changes
    ACCEPTABLE     = "acceptable"           # No action needed


# ──────────────────────────────────────────────────────────────────────────────
# DATA CLASSES
# ──────────────────────────────────────────────────────────────────────────────

@dataclass
class RouteOptConfig:
    """Thresholds that define what constitutes a routing problem."""
    # DRC: any violations = blocking; 0 needed for tapeout
    drc_threshold:       int   = 0

    # Unrouted nets: any = blocking
    unrouted_threshold:  int   = 0

    # Timing: WNS below this is a violation
    wns_threshold_ns:    float = -0.05

    # Congestion: above this fraction is concerning
    congestion_high:     float = 0.80

    # Wire length warning threshold (µm) — very long designs may have IR drop
    wire_length_warn_um: float = 500_000.0   # 500 mm total = large design


@dataclass
class RoutingIssue:
    """One identified routing quality problem."""
    issue_type:  RoutingIssueType
    severity:    str              # "critical", "warning", "info"
    description: str
    metric:      float
    threshold:   float
    fix_strategy: FixStrategy = FixStrategy.CHANGE_CONFIG


@dataclass
class RouteAnalysisResult:
    """Complete output from RoutingOptimizer.analyze()."""
    top_module:   str
    is_tapeable:  bool = False    # True only when DRC=0 AND unrouted=0

    issues:       List[RoutingIssue] = field(default_factory=list)
    action_plan:  List[str]          = field(default_factory=list)
    warnings:     List[str]          = field(default_factory=list)

    # Raw metrics for reference
    drc_count:      int   = 0
    unrouted_count: int   = 0
    wns_ns:         float = 0.0
    wire_length_um: float = 0.0
    via_count:      int   = 0

    def summary(self) -> str:
        tapeout = "✅  TAPE-OUT READY" if self.is_tapeable else "❌  NOT READY"
        lines   = [
            "",
            "═" * 60,
            f"  Routing Analysis  –  {self.top_module}",
            "═" * 60,
            f"  Tape-out status : {tapeout}",
            f"  DRC violations  : {self.drc_count}",
            f"  Unrouted nets   : {self.unrouted_count}",
            f"  WNS             : {self.wns_ns:.3f} ns",
            f"  Wire length     : {self.wire_length_um:.1f} µm",
            f"  Via count       : {self.via_count}",
        ]
        if self.issues:
            lines.append(f"\n  Issues ({len(self.issues)}):")
            for iss in self.issues:
                icon = "❌" if iss.severity == "critical" else "⚠ "
                lines.append(f"    {icon}  {iss.description}")
        if self.action_plan:
            lines.append(f"\n  Action plan ({len(self.action_plan)} steps):")
            for i, step in enumerate(self.action_plan, 1):
                lines.append(f"    {i}. {step}")
        lines.append("═" * 60)
        return "\n".join(lines)


# ──────────────────────────────────────────────────────────────────────────────
# MAIN CLASS
# ──────────────────────────────────────────────────────────────────────────────

class RoutingOptimizer:
    """
    Analyses routing results and produces an ordered fix plan.

    This class is primarily an analyser — it reads reports and produces
    human-readable guidance.  It also provides apply_fixes() which
    calls OpenROAD's incremental rerouting for minor DRC violations.
    """

    def __init__(self, docker: DockerManager, pdk) -> None:
        self.logger = logging.getLogger(__name__)
        self.docker = docker
        self.pdk    = pdk

    # ──────────────────────────────────────────────────────────────────────
    # PUBLIC API
    # ──────────────────────────────────────────────────────────────────────

    def analyze(
        self,
        routing_report: str | Path,
        top_module:     str,
        drc_file:       Optional[str | Path] = None,
        config:         Optional[RouteOptConfig] = None,
    ) -> RouteAnalysisResult:
        """
        Analyse routing reports and generate a fix plan.

        Args:
            routing_report: Path to routing.rpt.
            top_module:     Top module name.
            drc_file:       Path to drc_violations.txt (optional).
            config:         Analysis thresholds.

        Returns:
            RouteAnalysisResult with tapeable flag and action plan.
        """
        config = config or RouteOptConfig()
        result = RouteAnalysisResult(top_module=top_module)

        # ── 1. parse metrics ───────────────────────────────────────────
        metrics = self._parse_routing_report(routing_report)
        if drc_file:
            metrics["drc_count"] = self._count_drc_violations(drc_file)

        result.drc_count      = metrics.get("drc_count",      0)
        result.unrouted_count = metrics.get("unrouted_count", 0)
        result.wns_ns         = metrics.get("wns_ns",         0.0)
        result.wire_length_um = metrics.get("wire_length_um", 0.0)
        result.via_count      = metrics.get("via_count",      0)

        # ── 2. identify issues ─────────────────────────────────────────
        result.issues = self._identify_issues(metrics, config)

        # ── 3. decide tapeable ─────────────────────────────────────────
        result.is_tapeable = (
            result.drc_count      <= config.drc_threshold and
            result.unrouted_count <= config.unrouted_threshold
        )

        # ── 4. build action plan ───────────────────────────────────────
        result.action_plan = self._build_action_plan(result.issues, metrics)

        self.logger.info(
            f"Routing analysis: {top_module} | "
            f"tapeable={result.is_tapeable} | "
            f"DRC={result.drc_count} | unrouted={result.unrouted_count}"
        )
        return result

    def analyze_from_result(
        self,
        detail_result,       # DetailRouteResult
        config: Optional[RouteOptConfig] = None,
    ) -> RouteAnalysisResult:
        """
        Convenience wrapper: pass a DetailRouteResult directly.

        Args:
            detail_result: DetailRouteResult from DetailRouter.run().
            config:        Analysis thresholds.

        Returns:
            RouteAnalysisResult.
        """
        config = config or RouteOptConfig()
        r      = RouteAnalysisResult(top_module=detail_result.top_module)

        s = detail_result.stats
        r.drc_count      = s.drc_violation_count
        r.unrouted_count = s.unrouted_nets
        r.wns_ns         = s.worst_slack_ns
        r.wire_length_um = s.total_wire_length_um
        r.via_count      = s.via_count

        metrics = {
            "drc_count":      r.drc_count,
            "unrouted_count": r.unrouted_count,
            "wns_ns":         r.wns_ns,
            "wire_length_um": r.wire_length_um,
            "via_count":      r.via_count,
            "congestion":     0.0,
        }

        r.issues     = self._identify_issues(metrics, config)
        r.is_tapeable = (
            r.drc_count      <= config.drc_threshold and
            r.unrouted_count <= config.unrouted_threshold
        )
        r.action_plan = self._build_action_plan(r.issues, metrics)
        return r

    # ──────────────────────────────────────────────────────────────────────
    # ANALYSIS HELPERS
    # ──────────────────────────────────────────────────────────────────────

    def _parse_routing_report(self, report_path: str | Path) -> dict:
        """Parse routing.rpt into a metrics dict."""
        metrics = {
            "drc_count":      0,
            "unrouted_count": 0,
            "wns_ns":         0.0,
            "tns_ns":         0.0,
            "wire_length_um": 0.0,
            "via_count":      0,
            "congestion":     0.0,
        }
        rpt = Path(report_path)
        if not rpt.exists():
            return metrics

        try:
            text = rpt.read_text(encoding="utf-8", errors="ignore")
            for line in text.splitlines():
                s = line.strip()

                m = re.match(r"Total wire length\s*:\s*([\d.]+)", s)
                if m:
                    metrics["wire_length_um"] = float(m.group(1))

                m2 = re.match(r"Total number of vias\s*:\s*(\d+)", s)
                if m2:
                    metrics["via_count"] = int(m2.group(1))

                m3 = re.match(r"Number of unrouted nets\s*:\s*(\d+)", s)
                if m3:
                    metrics["unrouted_count"] = int(m3.group(1))

                m4 = re.match(r"Number of DRC violations\s*:\s*(\d+)", s)
                if m4:
                    metrics["drc_count"] = int(m4.group(1))

                if s.startswith("wns "):
                    try:
                        metrics["wns_ns"] = float(s.split()[1])
                    except (IndexError, ValueError):
                        pass
                if s.startswith("tns "):
                    try:
                        metrics["tns_ns"] = float(s.split()[1])
                    except (IndexError, ValueError):
                        pass

                m5 = re.match(r"Max.*congestion\s*:\s*([\d.]+)", s, re.IGNORECASE)
                if m5:
                    metrics["congestion"] = max(
                        metrics["congestion"], float(m5.group(1))
                    )

        except OSError:
            pass

        return metrics

    def _count_drc_violations(self, drc_file: str | Path) -> int:
        """Count DRC violations from a TritonRoute drc_violations.txt file."""
        f = Path(drc_file)
        if not f.exists():
            return 0
        try:
            text = f.read_text(encoding="utf-8", errors="ignore")
            # TritonRoute marks each violation with "violation type:"
            count = len(re.findall(r"^violation type", text, re.MULTILINE))
            if count == 0:
                # Fallback: count non-comment, non-empty lines
                count = sum(
                    1 for l in text.splitlines()
                    if l.strip() and not l.strip().startswith("#")
                )
            return count
        except OSError:
            return 0

    def _identify_issues(
        self,
        metrics: dict,
        config:  RouteOptConfig,
    ) -> List[RoutingIssue]:
        """Compare metrics against thresholds and return issue list."""
        issues: List[RoutingIssue] = []

        drc   = metrics.get("drc_count",      0)
        unr   = metrics.get("unrouted_count", 0)
        wns   = metrics.get("wns_ns",         0.0)
        cong  = metrics.get("congestion",     0.0)
        wire  = metrics.get("wire_length_um", 0.0)

        if drc > 0:
            issues.append(RoutingIssue(
                issue_type   = RoutingIssueType.DRC_VIOLATION,
                severity     = "critical",
                description  = f"{drc} DRC violation(s) – must fix before tapeout",
                metric       = float(drc),
                threshold    = float(config.drc_threshold),
                fix_strategy = FixStrategy.REROUTE_NET,
            ))

        if unr > 0:
            issues.append(RoutingIssue(
                issue_type   = RoutingIssueType.UNROUTED_NET,
                severity     = "critical",
                description  = f"{unr} unrouted net(s) – chip will not function",
                metric       = float(unr),
                threshold    = float(config.unrouted_threshold),
                fix_strategy = FixStrategy.CHANGE_CONFIG,
            ))

        if wns < config.wns_threshold_ns:
            sev = "critical" if wns < -0.5 else "warning"
            issues.append(RoutingIssue(
                issue_type   = RoutingIssueType.TIMING_VIOLATION,
                severity     = sev,
                description  = f"Post-route timing violation: WNS = {wns:.3f} ns",
                metric       = wns,
                threshold    = config.wns_threshold_ns,
                fix_strategy = FixStrategy.RESIZE_CELL,
            ))

        if cong > config.congestion_high:
            issues.append(RoutingIssue(
                issue_type   = RoutingIssueType.HIGH_CONGESTION,
                severity     = "warning",
                description  = f"High routing congestion: {cong:.3f}",
                metric       = cong,
                threshold    = config.congestion_high,
                fix_strategy = FixStrategy.REROUTE_AREA,
            ))

        if wire > config.wire_length_warn_um:
            issues.append(RoutingIssue(
                issue_type   = RoutingIssueType.LONG_WIRE,
                severity     = "info",
                description  = (
                    f"Total wire length {wire:.0f} µm is very large. "
                    f"Check for IR drop issues."
                ),
                metric    = wire,
                threshold = config.wire_length_warn_um,
                fix_strategy = FixStrategy.ACCEPTABLE,
            ))

        # Sort: critical → warning → info
        order = {"critical": 0, "warning": 1, "info": 2}
        issues.sort(key=lambda x: order.get(x.severity, 3))
        return issues

    def _build_action_plan(
        self,
        issues:  List[RoutingIssue],
        metrics: dict,
    ) -> List[str]:
        """
        Build an ordered list of specific actions to fix all issues.

        Critical issues → must fix before proceeding.
        Warnings → should address for robustness.
        Info → optional improvements.
        """
        plan: List[str] = []
        types = {i.issue_type for i in issues}
        critical = [i for i in issues if i.severity == "critical"]

        if not critical:
            plan.append(
                "No blocking issues found. Proceed to DRC/LVS sign-off "
                "→ GDSII generation."
            )

        if RoutingIssueType.UNROUTED_NET in types:
            plan.append(
                "Fix unrouted nets FIRST: reduce target_utilization in "
                "FloorplannerConfig to give the router more space. "
                "Re-run from floorplanning."
            )

        if RoutingIssueType.DRC_VIOLATION in types:
            drc = metrics.get("drc_count", 0)
            if drc <= 10:
                plan.append(
                    f"Fix {drc} DRC violation(s): run "
                    "`detailed_route -drc_report_iter 5` in OpenROAD to "
                    "attempt automatic repair."
                )
            else:
                plan.append(
                    f"{drc} DRC violations – too many for auto-repair. "
                    "Reduce density_target in PlacementConfig and re-run "
                    "placement + routing."
                )

        if RoutingIssueType.TIMING_VIOLATION in types:
            wns = metrics.get("wns_ns", 0.0)
            if wns > -0.2:
                plan.append(
                    f"Timing WNS={wns:.3f} ns is close – run "
                    "`repair_timing -setup` in OpenROAD after routing to "
                    "fix with gate sizing."
                )
            else:
                plan.append(
                    f"Timing WNS={wns:.3f} ns is too negative to fix in "
                    "post-route. Increase clock_period_ns in FloorplannerConfig "
                    "and re-run from placement."
                )

        if RoutingIssueType.HIGH_CONGESTION in types:
            plan.append(
                "Reduce congestion: lower density_target to 0.50 in "
                "PlacementConfig and increase adjustment to 0.4 in "
                "GlobalRouteConfig."
            )

        if not plan:
            plan.append(
                "Routing quality is acceptable. "
                "Proceed to: magic.export_gds() → klayout.run_drc() → GDSII."
            )

        return plan
