"""
detail_router.py  –  Detailed Routing for RTL-Gen AI
=====================================================
Runs TritonRoute (inside OpenROAD/Docker) to place exact wire segments
and vias that connect every net in the design.

What detailed routing does
───────────────────────────
Takes the route guides from global routing and:
  1. Assigns each net to specific routing tracks on each layer
  2. Inserts vias where wires change layers
  3. Enforces all DRC spacing and width rules
  4. Resolves routing conflicts (jogs, detours)
  5. Produces a fully-routed DEF where every net is physically connected

After detailed routing, the design is nearly tape-out ready.
The only remaining steps are:
  • DRC/LVS sign-off
  • GDSII generation

TritonRoute key concepts
─────────────────────────
  Access pattern:   How TritonRoute connects each pin to the wire grid
  Routing tracks:   Pre-defined wire positions on each metal layer
  DRC-correct:      Every wire satisfies minimum width, spacing, enclosure
  Via optimization: Minimize via count to reduce resistance

Sky130 design rule highlights (met2, typical)
  Min width:   0.14 µm
  Min spacing: 0.14 µm
  Via size:    0.15 × 0.15 µm

Data flow
──────────
  cts.def + route_guides.txt  →  detail_router.py  →  OpenROAD Docker
                               →  routed.def  (fully connected layout)
                               →  routing.rpt  (DRC violations, statistics)

Usage example
──────────────
    from python.docker_manager import DockerManager
    from python.pdk_manager    import PDKManager
    from python.detail_router  import DetailRouter, DetailRouteConfig

    dm = DockerManager()
    pdk = PDKManager()
    dr = DetailRouter(docker=dm, pdk=pdk)

    result = dr.run(
        def_path    = r"C:\\project\\physical\\cts.def",
        guide_path  = r"C:\\project\\physical\\route_guides.txt",
        top_module  = "adder_8bit",
        output_dir  = r"C:\\project\\physical",
    )
    print(result.summary())
    # Writes: routed.def, routing.rpt
"""

from __future__ import annotations

import logging
import re
import textwrap
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional

from python.docker_manager import DockerManager, ContainerResult


# ──────────────────────────────────────────────────────────────────────────────
# DATA CLASSES
# ──────────────────────────────────────────────────────────────────────────────

@dataclass
class DetailRouteConfig:
    """
    Parameters for TritonRoute detailed routing.

    Defaults are appropriate for most simple Sky130 designs.
    """
    # Clock settings for post-route STA
    clock_period_ns:    float = 10.0
    clock_net:          str   = "clk"

    # Minimum metal layer for signal routing (met2 avoids met1 power rails)
    min_layer:          str   = "met2"

    # Maximum signal layer (stay below met5 power stripes)
    max_layer:          str   = "met4"

    # Number of TritonRoute threads (higher = faster but more RAM)
    threads:            int   = 4

    # Maximum number of DRC repair iterations (0 = unlimited)
    # Each iteration attempts to fix remaining DRC violations
    drc_repair_loops:   int   = 3

    # Whether to run DRC check after routing and report violations
    run_drc_check:      bool  = True

    # Whether to run post-route STA and generate timing report
    run_sta:            bool  = True

    # Via optimization passes (more = fewer vias, longer runtime)
    via_opt_passes:     int   = 1


@dataclass
class RoutingStats:
    """
    Statistics extracted from the routing report.
    """
    total_wire_length_um: float = 0.0   # Total routed wire length
    via_count:            int   = 0     # Total vias inserted
    drc_violation_count:  int   = 0     # Remaining DRC violations (0 = clean)
    unrouted_nets:        int   = 0     # Nets that could not be routed (0 = all routed)
    worst_slack_ns:       float = 0.0   # WNS after post-route STA
    tns_ns:               float = 0.0   # TNS after post-route STA


@dataclass
class DetailRouteResult:
    """Complete result from DetailRouter.run()."""
    top_module:    str
    output_dir:    str
    success:       bool = False

    routed_def:    Optional[str] = None   # Path to routed.def  ← KEY OUTPUT
    report_path:   Optional[str] = None   # Path to routing.rpt
    stats:         RoutingStats = field(default_factory=RoutingStats)

    run_results:   List[RunResult] = field(default_factory=list)
    error_message: str = ""

    def is_drc_clean(self) -> bool:
        """True when routing completed with zero DRC violations."""
        return self.success and self.stats.drc_violation_count == 0

    def is_fully_routed(self) -> bool:
        """True when all nets are connected (no unrouted nets)."""
        return self.success and self.stats.unrouted_nets == 0

    def summary(self) -> str:
        status = "✅  SUCCESS" if self.success else "❌  FAILED"
        drc_s  = "✅  CLEAN"  if self.is_drc_clean() else \
                 f"❌  {self.stats.drc_violation_count} violations"
        s      = self.stats
        lines  = [
            "",
            "╔" + "═" * 58 + "╗",
            "║  Detailed Routing Result  –  RTL-Gen AI" + " " * 17 + "║",
            "╠" + "═" * 58 + "╣",
            f"║  Status          : {status:<37} ║",
            f"║  Top module      : {self.top_module:<37} ║",
        ]
        if self.success:
            lines += [
                "╠" + "─" * 58 + "╣",
                f"║  Wire length     : {s.total_wire_length_um:.1f} µm"
                + " " * max(0, 33 - len(f"{s.total_wire_length_um:.1f} µm")) + " ║",
                f"║  Via count       : {s.via_count:<37} ║",
                f"║  DRC violations  : {drc_s:<37} ║",
                f"║  Unrouted nets   : {s.unrouted_nets:<37} ║",
                f"║  WNS             : {s.worst_slack_ns:.3f} ns"
                + " " * max(0, 33 - len(f"{s.worst_slack_ns:.3f} ns")) + " ║",
            ]
        if self.routed_def:
            p = Path(self.routed_def).name
            lines.append(f"║  Routed DEF      : {p:<37} ║")
        if self.error_message:
            lines += [
                "╠" + "─" * 58 + "╣",
                f"║  Error           : {self.error_message[:37]:<37} ║",
            ]
        lines.append("╚" + "═" * 58 + "╝")
        return "\n".join(lines)


# ──────────────────────────────────────────────────────────────────────────────
# MAIN CLASS
# ──────────────────────────────────────────────────────────────────────────────

class DetailRouter:
    """
    Runs TritonRoute detailed routing via OpenROAD in Docker.

    Reads  : cts.def + route_guides.txt
    Writes : routed.def  (fully connected layout, ready for DRC/GDS)
             routing.rpt (wire stats, DRC violations, timing)
    """

    def __init__(self, docker: DockerManager, pdk) -> None:
        self.logger = logging.getLogger(__name__)
        self.docker = docker
        self.pdk    = pdk

    # ──────────────────────────────────────────────────────────────────────
    # PUBLIC API
    # ──────────────────────────────────────────────────────────────────────

    def run(
        self,
        def_path:   str | Path,
        top_module: str,
        output_dir: str | Path,
        guide_path: Optional[str | Path] = None,
        config:     Optional[DetailRouteConfig] = None,
    ) -> DetailRouteResult:
        """
        Run TritonRoute detailed routing.

        Args:
            def_path:   Path to cts.def on Windows.
            top_module: Top-level module name.
            output_dir: Windows output directory.
            guide_path: Path to route_guides.txt from global routing.
                        When None, expected at <output_dir>/route_guides.txt.
            config:     Routing parameters.

        Returns:
            DetailRouteResult with routed.def path and DRC statistics.
        """
        config     = config or DetailRouteConfig()
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        def_path   = Path(def_path)

        # Resolve guide file path
        if guide_path is None:
            guide_path = output_dir / "route_guides.txt"
        guide_path = Path(guide_path)

        result = DetailRouteResult(
            top_module = top_module,
            output_dir = str(output_dir),
        )

        self.logger.info(
            f"Detailed routing: {top_module} | "
            f"threads={config.threads} | "
            f"drc_loops={config.drc_repair_loops}"
        )

        # Copy input files to output_dir for Docker access at /work/
        import shutil
        for src in (def_path, guide_path):
            dst = output_dir / src.name
            if src.resolve() != dst.resolve() and src.exists():
                shutil.copy2(src, dst)

        tcl = self._generate_detail_route_script(
            def_path, guide_path, top_module, config
        )
        run = self.docker.run_script(
            script_content = tcl,
            script_name    = "detail_route.tcl",
            work_dir       = output_dir,
            timeout        = 3600,   # 1 hour — detailed routing is slow
        )
        result.run_results.append(run)

        if not run.success:
            result.error_message = self._extract_error(run.combined_output())
            self.logger.error(f"Detailed routing failed: {result.error_message}")
            return result

        # Collect output files
        routed_def = output_dir / "routed.def"
        rpt        = output_dir / "routing.rpt"

        result.routed_def   = str(routed_def) if routed_def.exists() else None
        result.report_path  = str(rpt)        if rpt.exists()        else None
        result.success      = routed_def.exists()

        if result.report_path:
            result.stats = self._parse_routing_report(Path(result.report_path))

        if not result.success:
            result.error_message = "routed.def not created"

        drc  = result.stats.drc_violation_count
        wire = result.stats.total_wire_length_um
        self.logger.info(
            f"Detailed routing {'complete' if result.success else 'FAILED'} | "
            f"DRC violations={drc} | wire={wire:.0f} µm"
        )
        return result

    def run_full_flow(
        self,
        def_path:   str | Path,
        top_module: str,
        output_dir: str | Path,
        config:     Optional[DetailRouteConfig] = None,
    ) -> DetailRouteResult:
        """
        Convenience method: runs global routing then detailed routing.

        Use this when you want to go from cts.def → routed.def in one call
        without managing the guide file explicitly.

        Args:
            def_path:   Path to cts.def.
            top_module: Top module name.
            output_dir: Output directory.
            config:     Routing config (shared settings for both stages).

        Returns:
            DetailRouteResult from the detailed routing stage.
        """
        from python.global_router import GlobalRouter, GlobalRouteConfig

        config     = config or DetailRouteConfig()
        output_dir = Path(output_dir)

        # Global routing first
        gr_config = GlobalRouteConfig(
            clock_period_ns = config.clock_period_ns,
            clock_net       = config.clock_net,
            min_layer       = config.min_layer,
            max_layer       = config.max_layer,
        )
        gr = GlobalRouter(docker=self.docker, pdk=self.pdk)
        gr_result = gr.run(def_path, top_module, output_dir, gr_config)

        if not gr_result.success:
            return DetailRouteResult(
                top_module    = top_module,
                output_dir    = str(output_dir),
                success       = False,
                error_message = f"Global routing failed: {gr_result.error_message}",
            )

        # Detailed routing
        return self.run(
            def_path   = def_path,
            top_module = top_module,
            output_dir = output_dir,
            guide_path = gr_result.guide_path,
            config     = config,
        )

    # ──────────────────────────────────────────────────────────────────────
    # TCL GENERATOR
    # ──────────────────────────────────────────────────────────────────────

    def _generate_detail_route_script(
        self,
        def_path:   Path,
        guide_path: Path,
        top_module: str,
        config:     DetailRouteConfig,
    ) -> str:
        """
        Generate the TritonRoute detailed routing Tcl script.

        Key commands:
          detailed_route            – run TritonRoute
          -output_drc               – write DRC violation list
          check_placement           – verify no cells moved
          report_check_types        – list violated DRC rules
        """
        tech_lef = "/pdk/sky130A/libs.ref/sky130_fd_sc_hd/lef/sky130_fd_sc_hd.tlef"
        cell_lef = "/pdk/sky130A/libs.ref/sky130_fd_sc_hd/lef/sky130_fd_sc_hd.lef"
        lib_tt   = "/pdk/sky130A/libs.ref/sky130_fd_sc_hd/lib/sky130_fd_sc_hd__tt_025C_1v80.lib"
        lib_ss   = "/pdk/sky130A/libs.ref/sky130_fd_sc_hd/lib/sky130_fd_sc_hd__ss_100C_1v60.lib"

        sta_section = ""
        if config.run_sta:
            sta_section = (
                "\n# ── 8. Post-route static timing analysis ───────────────────\n"
                "set_propagated_clock [all_clocks]\n"
                "report_checks -path_delay max -format full_clock >> /work/routing.rpt\n"
                "report_wns >> /work/routing.rpt\n"
                "report_tns >> /work/routing.rpt\n"
            )

        drc_section = ""
        if config.run_drc_check:
            drc_section = (
                "\n# ── 7. DRC check report ─────────────────────────────────────\n"
                "check_placement -verbose\n"
                "set_check_types -max_slew\n"
                "report_check_types >> /work/routing.rpt\n"
            )

        return textwrap.dedent(f"""
        # ────────────────────────────────────────────────────────────────
        # Detailed Routing (TritonRoute)  –  RTL-Gen AI
        # Top module  : {top_module}
        # Layers      : {config.min_layer} – {config.max_layer}
        # Threads     : {config.threads}
        # ────────────────────────────────────────────────────────────────

        # ── 1. Read PDK files ─────────────────────────────────────────
        read_lef     {tech_lef}
        read_lef     {cell_lef}
        read_liberty {lib_tt}
        read_liberty {lib_ss}

        # ── 2. Read post-CTS DEF ─────────────────────────────────────
        read_def /work/{def_path.name}
        link_design {top_module}

        # ── 3. Clock constraint ───────────────────────────────────────
        create_clock -name {config.clock_net} \\
                     -period {config.clock_period_ns} \\
                     [get_ports {config.clock_net}]

        # ── 4. Load global route guides ───────────────────────────────
        # Route guides tell TritonRoute which layers/tiles to use per net
        read_guides /work/{guide_path.name}

        # ── 5. Set routing layer bounds ───────────────────────────────
        set_routing_layers -signal {{{config.min_layer} {config.max_layer}}}

        # ── 6. Run TritonRoute detailed routing ───────────────────────
        # -output_drc       : write DRC violations to file
        # -output_maze      : write maze routing debug log
        # -verbose          : output level (1 = standard)
        detailed_route \\
            -output_drc  /work/drc_violations.txt \\
            -output_maze /work/maze.log \\
            -verbose 1
        {drc_section}
        {sta_section}
        # ── 9. Wire length and via statistics ─────────────────────────
        report_design_area          >> /work/routing.rpt
        report_wire_length          >> /work/routing.rpt

        # ── 10. Write fully-routed DEF ────────────────────────────────
        write_def /work/routed.def

        puts "\\n✅  Detailed routing complete: {top_module}\\n"
        exit
        """).strip()

    # ──────────────────────────────────────────────────────────────────────
    # REPORT PARSING
    # ──────────────────────────────────────────────────────────────────────

    def _parse_routing_report(self, rpt_path: Path) -> RoutingStats:
        """
        Parse routing.rpt + drc_violations.txt for routing quality metrics.

        Lines parsed:
          "Total wire length: N.N um"
          "Total number of vias: N"
          "Number of DRC violations: N"
          "Number of unrouted nets: N"
          "wns X.XX"
        """
        stats = RoutingStats()
        if not rpt_path.exists():
            return stats

        # Also look for drc_violations.txt alongside the report
        drc_file = rpt_path.parent / "drc_violations.txt"

        try:
            text = rpt_path.read_text(encoding="utf-8", errors="ignore")
            for line in text.splitlines():
                s = line.strip()

                # Wire length
                m = re.match(r"Total wire length\s*:\s*([\d.]+)", s)
                if m:
                    stats.total_wire_length_um = float(m.group(1))

                # Via count
                m2 = re.match(r"Total number of vias\s*:\s*(\d+)", s)
                if m2:
                    stats.via_count = int(m2.group(1))

                # Unrouted nets
                m3 = re.match(r"Number of unrouted nets\s*:\s*(\d+)", s)
                if m3:
                    stats.unrouted_nets = int(m3.group(1))

                # WNS / TNS
                if s.startswith("wns "):
                    try:
                        stats.worst_slack_ns = float(s.split()[1])
                    except (IndexError, ValueError):
                        pass
                if s.startswith("tns "):
                    try:
                        stats.tns_ns = float(s.split()[1])
                    except (IndexError, ValueError):
                        pass

        except OSError:
            pass

        # Parse DRC violation count from drc_violations.txt
        if drc_file.exists():
            try:
                drc_text = drc_file.read_text(encoding="utf-8", errors="ignore")
                # Each "violation" block starts with "violation type"
                violations = re.findall(r"^violation type", drc_text, re.MULTILINE)
                stats.drc_violation_count = len(violations)
                # Fallback: count non-empty lines
                if stats.drc_violation_count == 0:
                    nonempty = [
                        l for l in drc_text.splitlines()
                        if l.strip() and not l.strip().startswith("#")
                    ]
                    stats.drc_violation_count = len(nonempty)
            except OSError:
                pass

        return stats

    @staticmethod
    def _extract_error(output: str) -> str:
        for line in output.splitlines():
            s = line.strip()
            if s.startswith(("[ERROR", "Error:", "ERROR:")):
                return s[:200]
        return "Detailed routing error (check run log)"
