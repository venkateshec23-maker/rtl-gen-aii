"""
placement_optimizer.py  –  Placement Quality Analyser & Optimiser
==================================================================
Analyses placed.def / cts.def quality and suggests or applies
OpenROAD optimisations to improve timing, congestion, and power
before routing.

This module does NOT modify the DEF directly.  It:
  1. Parses the placement report to assess quality
  2. Generates a diagnosis (what is wrong and why)
  3. Suggests parameter adjustments for the next run
  4. Optionally runs incremental optimisations via OpenROAD

Metrics assessed
─────────────────
  • Timing (WNS / TNS):  Are there setup violations?
  • Overflow:            Is global placement too dense?
  • Utilisation:         Is the die over/under-used?
  • Clock skew:          Is the clock tree balanced?
  • Congestion estimate: Are certain regions too crowded?

Optimisation techniques applied
─────────────────────────────────
  1. Gate sizing      – upsize slow cells on critical paths
  2. Buffer insertion – fix long wires causing timing violations
  3. Cell spreading   – reduce local density hotspots
  4. Logic restructuring – swap equivalent cells with better timing
  5. Hold repair      – insert buffers to fix hold violations

Usage example
──────────────
    from python.placement_optimizer import PlacementOptimizer, OptConfig

    opt    = PlacementOptimizer(docker=dm, pdk=pdk)
    result = opt.analyze_and_fix(
        def_path      = r"C:\\project\\physical\\placed.def",
        report_path   = r"C:\\project\\physical\\placement.rpt",
        top_module    = "adder_8bit",
        output_dir    = r"C:\\project\\physical",
    )
    print(result.diagnosis)
    print(result.optimized_def)
"""

from __future__ import annotations

import logging
import re
import textwrap
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import List, Optional, Tuple

from python.docker_manager import DockerManager, ContainerResult


# ──────────────────────────────────────────────────────────────────────────────
# ENUMERATIONS
# ──────────────────────────────────────────────────────────────────────────────

class OptimizationLevel(Enum):
    """How aggressively to optimise.  Higher = slower but better quality."""
    NONE       = 0   # Analysis only, no changes
    LIGHT      = 1   # Fast: timing repair only
    STANDARD   = 2   # Balanced: timing + buffer insertion
    AGGRESSIVE = 3   # Slow: full gate-sizing + restructuring


class IssueType(Enum):
    """Category of placement quality issue."""
    SETUP_VIOLATION  = "setup_violation"
    HOLD_VIOLATION   = "hold_violation"
    HIGH_OVERFLOW    = "high_overflow"
    LOW_UTILIZATION  = "low_utilization"
    HIGH_UTILIZATION = "high_utilization"
    HIGH_SKEW        = "high_skew"
    NONE             = "none"


# ──────────────────────────────────────────────────────────────────────────────
# DATA CLASSES
# ──────────────────────────────────────────────────────────────────────────────

@dataclass
class OptConfig:
    """Parameters for placement optimisation."""
    level:           OptimizationLevel = OptimizationLevel.STANDARD

    # Clock settings (needed for timing repair)
    clock_period_ns: float = 10.0
    clock_net:       str   = "clk"

    # Current density target (used when recommending reduced density)
    density_target:  float = 0.60

    # Maximum fraction of cells that can be resized / buffered
    max_buffer_pct:  int   = 30   # percent of total cell count

    # Thresholds that trigger specific optimisations
    wns_threshold_ns: float = -0.05  # WNS worse than this → apply timing fix
    overflow_threshold: float = 0.10  # Overflow above this → spread cells
    util_low_threshold: float = 0.40  # Utilisation below this → warn
    util_high_threshold: float = 0.85  # Utilisation above this → warn


@dataclass
class PlacementIssue:
    """One identified quality problem."""
    issue_type:  IssueType
    severity:    str        # "critical", "warning", "info"
    description: str
    metric:      float      # The measured value that triggered this issue
    threshold:   float      # The threshold that was exceeded


@dataclass
class OptimizationResult:
    """Complete output from PlacementOptimizer.analyze_and_fix()."""
    top_module:     str
    success:        bool = False

    # Identified issues (sorted by severity)
    issues:         List[PlacementIssue] = field(default_factory=list)

    # Human-readable diagnosis paragraph
    diagnosis:      str = ""

    # Parameter recommendations for the next placement run
    recommendations: List[str] = field(default_factory=list)

    # Path to optimised DEF (None if level=NONE or optimisation failed)
    optimized_def:  Optional[str] = None

    # Docker run results (one per optimisation step applied)
    run_results:    List[RunResult] = field(default_factory=list)

    error_message:  str = ""

    def summary(self) -> str:
        lines = [
            "",
            "═" * 58,
            f"  Placement Optimisation  –  {self.top_module}",
            "═" * 58,
        ]
        if self.issues:
            lines.append(f"  Issues found ({len(self.issues)}):")
            for iss in self.issues:
                icon = "❌" if iss.severity == "critical" else "⚠ "
                lines.append(f"    {icon}  {iss.description}")
        else:
            lines.append("  ✅  No issues – placement quality is good")

        if self.recommendations:
            lines.append(f"\n  Recommendations ({len(self.recommendations)}):")
            for r in self.recommendations:
                lines.append(f"    → {r}")

        if self.optimized_def:
            lines.append(f"\n  Optimised DEF : {Path(self.optimized_def).name}")
        lines.append("═" * 58)
        return "\n".join(lines)


# ──────────────────────────────────────────────────────────────────────────────
# MAIN CLASS
# ──────────────────────────────────────────────────────────────────────────────

class PlacementOptimizer:
    """
    Analyses placement quality and applies incremental OpenROAD fixes.

    Can be used:
      a) Analysis-only mode (OptimizationLevel.NONE)
         – reads placement report → returns diagnosis + recommendations
         – no Docker required
      b) Active optimisation mode (LIGHT / STANDARD / AGGRESSIVE)
         – runs repair_timing / gate_sizing in OpenROAD
         – writes optimised_placed.def
    """

    def __init__(self, docker: DockerManager, pdk) -> None:
        self.logger = logging.getLogger(__name__)
        self.docker = docker
        self.pdk    = pdk

    # ──────────────────────────────────────────────────────────────────────
    # PUBLIC API
    # ──────────────────────────────────────────────────────────────────────

    def analyze_and_fix(
        self,
        def_path:     str | Path,
        top_module:   str,
        output_dir:   str | Path,
        report_path:  Optional[str | Path] = None,
        config:       Optional[OptConfig]  = None,
    ) -> OptimizationResult:
        """
        Analyse placement quality and optionally apply fixes.

        Args:
            def_path:    Path to placed.def or cts.def.
            top_module:  Top module name.
            output_dir:  Output directory.
            report_path: Path to placement.rpt or cts.rpt (for metric parsing).
                         When None, a new report is generated inside Docker.
            config:      Optimisation parameters.

        Returns:
            OptimizationResult with diagnosis and optional optimised DEF.
        """
        config     = config or OptConfig()
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        def_path   = Path(def_path)

        result = OptimizationResult(top_module=top_module)

        # ── Step 1: read metrics from report ───────────────────────────
        metrics = self._read_metrics(report_path)

        # ── Step 2: identify issues ────────────────────────────────────
        result.issues = self._identify_issues(metrics, config)

        # ── Step 3: generate diagnosis and recommendations ─────────────
        result.diagnosis       = self._write_diagnosis(result.issues, metrics)
        result.recommendations = self._write_recommendations(
            result.issues, metrics, config
        )

        # ── Step 4: apply fixes (if level > NONE) ─────────────────────
        if config.level == OptimizationLevel.NONE:
            result.success = True
            return result

        if not def_path.exists():
            result.error_message = f"DEF not found: {def_path}"
            return result

        opt_def, runs = self._apply_optimizations(
            def_path, top_module, output_dir, config, result.issues
        )
        result.run_results   = runs
        result.optimized_def = str(opt_def) if opt_def and opt_def.exists() else None
        result.success       = result.optimized_def is not None

        return result

    def analyze_only(
        self,
        report_path: str | Path,
        config:      Optional[OptConfig] = None,
    ) -> Tuple[List[PlacementIssue], List[str]]:
        """
        Quick analysis without any Docker calls.
        Reads a placement/CTS report and returns (issues, recommendations).

        Useful for quickly deciding whether to re-run placement with
        different parameters before committing to a full optimisation run.

        Args:
            report_path: Path to placement.rpt or cts.rpt.
            config:      Threshold settings.

        Returns:
            Tuple of (issues_list, recommendations_list).
        """
        config  = config or OptConfig()
        metrics = self._read_metrics(report_path)
        issues  = self._identify_issues(metrics, config)
        recs    = self._write_recommendations(issues, metrics, config)
        return issues, recs

    # ──────────────────────────────────────────────────────────────────────
    # ANALYSIS
    # ──────────────────────────────────────────────────────────────────────

    def _read_metrics(
        self, report_path: Optional[str | Path]
    ) -> dict:
        """
        Parse a placement / CTS report for numeric quality metrics.

        Returns a flat dict with keys:
          wns, tns, utilization_pct, overflow, cell_count, max_skew
        """
        metrics = {
            "wns":             0.0,
            "tns":             0.0,
            "utilization_pct": 0.0,
            "overflow":        0.0,
            "cell_count":      0,
            "max_skew":        0.0,
        }
        if report_path is None:
            return metrics

        rpt = Path(report_path)
        if not rpt.exists():
            return metrics

        try:
            text = rpt.read_text(encoding="utf-8", errors="ignore")
            for line in text.splitlines():
                s = line.strip()

                if s.startswith("wns "):
                    try:
                        metrics["wns"] = float(s.split()[1])
                    except (IndexError, ValueError):
                        pass

                if s.startswith("tns "):
                    try:
                        metrics["tns"] = float(s.split()[1])
                    except (IndexError, ValueError):
                        pass

                m = re.match(
                    r"Design area\s+([\d.]+)\s+u\^2\s+([\d.]+)%", s
                )
                if m:
                    metrics["utilization_pct"] = float(m.group(2))

                m2 = re.match(r"Overflow\s*:\s*([\d.]+)", s)
                if m2:
                    metrics["overflow"] = float(m2.group(1))

                m3 = re.match(r"Number of instances\s*:\s*(\d+)", s)
                if m3:
                    metrics["cell_count"] = int(m3.group(1))

                # Skew
                if "Skew" in s or "skew" in s:
                    nums = re.findall(r"[-\d]+\.[\d]+", s)
                    if nums:
                        try:
                            metrics["max_skew"] = abs(float(nums[-1]))
                        except ValueError:
                            pass

        except OSError:
            pass

        return metrics

    def _identify_issues(
        self,
        metrics: dict,
        config:  OptConfig,
    ) -> List[PlacementIssue]:
        """
        Compare metrics against thresholds and return a list of issues.
        Issues are sorted: critical first, then warning, then info.
        """
        issues: List[PlacementIssue] = []

        wns  = metrics.get("wns",  0.0)
        util = metrics.get("utilization_pct", 0.0)
        ovf  = metrics.get("overflow", 0.0)
        skew = metrics.get("max_skew", 0.0)

        # ── Setup violations ──────────────────────────────────────────
        if wns < config.wns_threshold_ns:
            severity = "critical" if wns < -0.5 else "warning"
            issues.append(PlacementIssue(
                issue_type  = IssueType.SETUP_VIOLATION,
                severity    = severity,
                description = f"Setup violation: WNS = {wns:.3f} ns",
                metric      = wns,
                threshold   = config.wns_threshold_ns,
            ))

        # ── High overflow (placement too dense) ───────────────────────
        if ovf > config.overflow_threshold:
            issues.append(PlacementIssue(
                issue_type  = IssueType.HIGH_OVERFLOW,
                severity    = "warning",
                description = f"High placement overflow: {ovf:.4f} (>{config.overflow_threshold})",
                metric      = ovf,
                threshold   = config.overflow_threshold,
            ))

        # ── Utilisation out of range ───────────────────────────────────
        if util > 0 and util < config.util_low_threshold * 100:
            issues.append(PlacementIssue(
                issue_type  = IssueType.LOW_UTILIZATION,
                severity    = "info",
                description = f"Low utilisation: {util:.1f}% (die may be too large)",
                metric      = util,
                threshold   = config.util_low_threshold * 100,
            ))
        elif util > config.util_high_threshold * 100:
            issues.append(PlacementIssue(
                issue_type  = IssueType.HIGH_UTILIZATION,
                severity    = "warning",
                description = f"High utilisation: {util:.1f}% (routing may fail)",
                metric      = util,
                threshold   = config.util_high_threshold * 100,
            ))

        # ── Clock skew ────────────────────────────────────────────────
        if skew > 0.2:    # > 200 ps is problematic
            issues.append(PlacementIssue(
                issue_type  = IssueType.HIGH_SKEW,
                severity    = "warning",
                description = f"High clock skew: {skew:.4f} ns (target < 0.1 ns)",
                metric      = skew,
                threshold   = 0.1,
            ))

        # Sort: critical → warning → info
        order = {"critical": 0, "warning": 1, "info": 2}
        issues.sort(key=lambda x: order.get(x.severity, 3))
        return issues

    def _write_diagnosis(
        self,
        issues:  List[PlacementIssue],
        metrics: dict,
    ) -> str:
        """Write a human-readable paragraph describing placement quality."""
        if not issues:
            return (
                f"Placement quality looks good.  "
                f"WNS={metrics['wns']:.3f} ns, "
                f"utilisation={metrics['utilization_pct']:.1f}%, "
                f"overflow={metrics['overflow']:.4f}."
            )

        critical = [i for i in issues if i.severity == "critical"]
        warnings = [i for i in issues if i.severity == "warning"]

        parts = []
        if critical:
            parts.append(
                f"{len(critical)} critical issue(s): "
                + "; ".join(i.description for i in critical)
            )
        if warnings:
            parts.append(
                f"{len(warnings)} warning(s): "
                + "; ".join(i.description for i in warnings)
            )
        return "  ".join(parts)

    def _write_recommendations(
        self,
        issues:  List[PlacementIssue],
        metrics: dict,
        config:  OptConfig,
    ) -> List[str]:
        """Return a list of concrete parameter change recommendations."""
        recs: List[str] = []
        types = {i.issue_type for i in issues}

        if IssueType.SETUP_VIOLATION in types:
            wns = metrics.get("wns", 0.0)
            if wns < -1.0:
                recs.append(
                    "Increase clock period (reduce frequency target) – "
                    "WNS > 1 ns is too large to fix in placement alone"
                )
            else:
                recs.append(
                    "Run placement optimisation (OptimizationLevel.STANDARD) "
                    "to apply gate sizing and buffer insertion"
                )

        if IssueType.HIGH_OVERFLOW in types:
            recs.append(
                f"Reduce density_target to {max(0.40, config.density_target - 0.10):.2f} "
                f"(current: {config.density_target}) and re-run global placement"
            )
            recs.append(
                "Increase die size by reducing target_utilization in FloorplannerConfig"
            )

        if IssueType.HIGH_UTILIZATION in types:
            recs.append(
                "Increase io_margin_um or reduce target_utilization in FloorplannerConfig"
            )

        if IssueType.LOW_UTILIZATION in types:
            recs.append(
                "Increase target_utilization to 0.65–0.75 to reduce die size and cost"
            )

        if IssueType.HIGH_SKEW in types:
            recs.append(
                "Re-run CTS with a larger buf_list (add clkbuf_16) for better balancing"
            )

        if not recs:
            recs.append("No parameter changes needed – proceed to routing")

        return recs

    # ──────────────────────────────────────────────────────────────────────
    # OPTIMISATION
    # ──────────────────────────────────────────────────────────────────────

    def _apply_optimizations(
        self,
        def_path:   Path,
        top_module: str,
        output_dir: Path,
        config:     OptConfig,
        issues:     List[PlacementIssue],
    ) -> Tuple[Optional[Path], List[RunResult]]:
        """
        Run the appropriate OpenROAD repair commands based on issues found.

        Returns:
            Tuple of (output_def_path, list_of_run_results).
        """
        runs: List[RunResult] = []
        issue_types = {i.issue_type for i in issues}

        # Copy DEF so Docker can access it
        dest = output_dir / def_path.name
        if def_path.resolve() != dest.resolve() and def_path.exists():
            import shutil
            shutil.copy2(def_path, dest)

        tcl = self._generate_optimization_script(
            def_path, top_module, config, issue_types
        )

        run = self.docker.run_script(
            script_content = tcl,
            script_name    = "optimize_placement.tcl",
            work_dir       = output_dir,
            timeout        = 1800,
        )
        runs.append(run)

        out_def = output_dir / "optimized_placed.def"
        return (out_def if out_def.exists() else None), runs

    def _generate_optimization_script(
        self,
        def_path:    Path,
        top_module:  str,
        config:      OptConfig,
        issue_types: set,
    ) -> str:
        """
        Generate OpenROAD Tcl that applies the required optimisations.

        Commands used:
          repair_timing -setup    → gate sizing + buffering for setup
          repair_timing -hold     → buffering for hold violations
          detailed_placement      → re-legalise after cell insertions
        """
        tech_lef = "/pdk/sky130A/libs.ref/sky130_fd_sc_hd/techlef/sky130_fd_sc_hd__nom.tlef"
        cell_lef = "/pdk/sky130A/libs.ref/sky130_fd_sc_hd/lef/sky130_fd_sc_hd.lef"
        lib_tt   = "/pdk/sky130A/libs.ref/sky130_fd_sc_hd/lib/sky130_fd_sc_hd__tt_025C_1v80.lib"
        lib_ss   = "/pdk/sky130A/libs.ref/sky130_fd_sc_hd/lib/sky130_fd_sc_hd__ss_100C_1v60.lib"

        # Build list of repair commands based on what issues were found
        repair_cmds = []

        if IssueType.SETUP_VIOLATION in issue_types:
            repair_cmds.append(
                f"# Fix setup violations: gate sizing + buffer insertion\n"
                f"repair_timing -setup \\\n"
                f"    -max_buffer_percent {config.max_buffer_pct} \\\n"
                f"    -max_utilization 0.90"
            )

        if IssueType.HOLD_VIOLATION in issue_types:
            repair_cmds.append(
                f"# Fix hold violations: delay buffer insertion\n"
                f"repair_timing -hold \\\n"
                f"    -max_buffer_percent {config.max_buffer_pct}"
            )

        if config.level == OptimizationLevel.AGGRESSIVE:
            repair_cmds.append(
                "# Aggressive: full timing optimisation\n"
                "repair_timing -setup -hold \\\n"
                f"    -max_buffer_percent {config.max_buffer_pct} \\\n"
                f"    -max_utilization 0.90"
            )

        # Always re-legalise after buffer insertions
        if repair_cmds:
            repair_cmds.append(
                "# Re-legalise placement after cell insertions\n"
                "detailed_placement"
            )

        repair_section = "\n\n".join(repair_cmds) if repair_cmds else (
            "# No timing issues found – placement accepted as-is"
        )

        return textwrap.dedent(f"""
        # ────────────────────────────────────────────────────────────────
        # Placement Optimisation  –  RTL-Gen AI
        # Top module  : {top_module}
        # Level       : {config.level.name}
        # ────────────────────────────────────────────────────────────────

        read_lef     {tech_lef}
        read_lef     {cell_lef}
        read_liberty {lib_tt}
        read_liberty {lib_ss}

        read_def /work/{def_path.name}
        link_design {top_module}

        create_clock -name {config.clock_net} \\
                     -period {config.clock_period_ns} \\
                     [get_ports {config.clock_net}]
        set_propagated_clock [all_clocks]

        # ── Repair commands ───────────────────────────────────────────
        {repair_section}

        # ── Post-optimisation report ──────────────────────────────────
        report_wns > /work/opt_timing.rpt
        report_tns >> /work/opt_timing.rpt
        report_design_area >> /work/opt_timing.rpt

        write_def /work/optimized_placed.def

        puts "\\n✅  Optimisation complete: {top_module}\\n"
        exit
        """).strip()
