"""
global_router.py  –  Global Routing for RTL-Gen AI
====================================================
Runs FastRoute (inside OpenROAD/Docker) to assign each net to a set of
routing tracks on the chip, without yet determining exact wire geometry.

What global routing does
─────────────────────────
Global routing is the first of two routing stages:

  Stage 1 – Global routing  (THIS FILE)
      Divides the chip into a grid of routing tiles (GCells).
      Assigns each net to a sequence of GCells connecting source to sink.
      Produces a "route guide" file — a high-level plan for the
      detailed router.  Does NOT place actual wires.

  Stage 2 – Detailed routing  (detail_router.py)
      Reads route guides and places exact wire segments.
      Resolves spacing/width DRC rules.
      Fills in vias.

Why global routing first?
──────────────────────────
Detailed routing is slow and cannot easily backtrack across the chip.
Global routing gives the detailed router a good starting point, avoiding
the need for global rerouting on congestion failures.

FastRoute settings used
────────────────────────
  -adjustment       : fraction of routing capacity reserved for detail router
  -layer_adjustments: per-layer capacity adjustments for Sky130
  -verbose          : output detail level (0–3)

Sky130 routing layers
───────────────────────
  met1 (H) – thin, horizontal,  used for power rails
  met2 (V) – thin, vertical,    primary signal layer
  met3 (H) – medium, horizontal
  met4 (V) – medium, vertical
  met5 (H) – thick, horizontal, used for power stripes

Signal nets primarily use met2–met4.

Data flow
──────────
  cts.def  →  global_router.py  →  OpenROAD Docker
           →  route_guides.txt  (consumed by detail_router.py)
           →  global_routed.def (intermediate checkpoint)
           →  congestion.rpt

Usage example
──────────────
    from python.docker_manager import DockerManager
    from python.pdk_manager    import PDKManager
    from python.global_router  import GlobalRouter, GlobalRouteConfig

    dm = DockerManager()
    pdk = PDKManager()
    gr = GlobalRouter(docker=dm, pdk=pdk)

    result = gr.run(
        def_path   = r"C:\\project\\physical\\cts.def",
        top_module = "adder_8bit",
        output_dir = r"C:\\project\\physical",
    )
    print(result.summary())
    # Writes: route_guides.txt, global_routed.def, congestion.rpt
"""

from __future__ import annotations

import logging
import re
import textwrap
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional

from python.docker_manager import DockerManager, ContainerResult


# ──────────────────────────────────────────────────────────────────────────────
# DATA CLASSES
# ──────────────────────────────────────────────────────────────────────────────

@dataclass
class GlobalRouteConfig:
    """
    Parameters for FastRoute global routing.

    Defaults are suitable for straightforward Sky130 designs.
    Increase adjustment if the detailed router reports congestion.
    """
    # Clock period (ns) — used to drive timing-aware routing order
    clock_period_ns:   float = 10.0
    clock_net:         str   = "clk"

    # Fraction of routing capacity to reserve for the detail router (0.0–1.0).
    # 0.3 = keep 30% headroom; detail router fills the rest.
    # Higher values → less congestion but may make some nets unroutable.
    adjustment:        float = 0.30

    # Minimum and maximum routing layers for signal nets
    min_layer:         str   = "met2"   # never route below met2
    max_layer:         str   = "met4"   # never route above met4 for signals

    # GCell grid size in number of sites.
    # Smaller = more tiles = more routing flexibility but slower.
    gcell_grid:        int   = 15

    # Verbose output level: 0=quiet, 1=normal, 2=detailed, 3=debug
    verbose:           int   = 1

    # Per-layer capacity adjustments (reduces congestion on crowded layers)
    # Dict of layer_name → adjustment fraction (0.0–1.0)
    layer_adjustments: Dict[str, float] = field(
        default_factory=lambda: {
            "met1": 0.0,   # met1 reserved for power rails → no signal routing
            "met2": 0.5,   # 50% capacity for signals
            "met3": 0.5,
            "met4": 0.4,
            "met5": 0.0,   # met5 reserved for power stripes
        }
    )


@dataclass
class CongestionStats:
    """
    Per-layer congestion statistics from the global routing report.
    Values are fractions: 1.0 = 100% of routing capacity used.
    """
    max_congestion:   float = 0.0    # Worst tile congestion across all layers
    avg_congestion:   float = 0.0    # Average congestion
    overflow_count:   int   = 0      # Tiles exceeding 100% capacity
    wirelength_um:    float = 0.0    # Total estimated wirelength


@dataclass
class GlobalRouteResult:
    """Complete result from GlobalRouter.run()."""
    top_module:     str
    output_dir:     str
    success:        bool = False

    guide_path:     Optional[str] = None   # route_guides.txt
    def_path:       Optional[str] = None   # global_routed.def
    report_path:    Optional[str] = None   # congestion.rpt
    congestion:     CongestionStats = field(default_factory=CongestionStats)

    run_results:    List[RunResult] = field(default_factory=list)
    error_message:  str = ""

    def summary(self) -> str:
        status = "✅  SUCCESS" if self.success else "❌  FAILED"
        c      = self.congestion
        lines  = [
            "",
            "╔" + "═" * 58 + "╗",
            "║  Global Routing Result  –  RTL-Gen AI" + " " * 19 + "║",
            "╠" + "═" * 58 + "╣",
            f"║  Status         : {status:<38} ║",
            f"║  Top module     : {self.top_module:<38} ║",
        ]
        if self.success:
            lines += [
                "╠" + "─" * 58 + "╣",
                f"║  Max congestion : {c.max_congestion:.3f}"
                + " " * max(0, 37 - len(f"{c.max_congestion:.3f}")) + " ║",
                f"║  Avg congestion : {c.avg_congestion:.3f}"
                + " " * max(0, 37 - len(f"{c.avg_congestion:.3f}")) + " ║",
                f"║  Overflow tiles : {c.overflow_count:<38} ║",
                f"║  Est wirelength : {c.wirelength_um:.1f} µm"
                + " " * max(0, 34 - len(f"{c.wirelength_um:.1f} µm")) + " ║",
            ]
        if self.guide_path:
            lines.append(
                f"║  Route guides   : {Path(self.guide_path).name:<38} ║"
            )
        if self.error_message:
            lines += [
                "╠" + "─" * 58 + "╣",
                f"║  Error          : {self.error_message[:38]:<38} ║",
            ]
        lines.append("╚" + "═" * 58 + "╝")
        return "\n".join(lines)


# ──────────────────────────────────────────────────────────────────────────────
# MAIN CLASS
# ──────────────────────────────────────────────────────────────────────────────

class GlobalRouter:
    """
    Runs FastRoute global routing via OpenROAD in Docker.

    Reads  : cts.def  (from CTSEngine)
    Writes : route_guides.txt, global_routed.def, congestion.rpt
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
        config:     Optional[GlobalRouteConfig] = None,
    ) -> GlobalRouteResult:
        """
        Run FastRoute global routing on a placed-and-CTS design.

        Args:
            def_path:   Path to cts.def on Windows.
            top_module: Top-level module name.
            output_dir: Windows output directory.
            config:     Routing parameters.

        Returns:
            GlobalRouteResult with route guide path and congestion stats.
        """
        config     = config or GlobalRouteConfig()
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        def_path   = Path(def_path)

        result = GlobalRouteResult(
            top_module = top_module,
            output_dir = str(output_dir),
        )

        self.logger.info(
            f"Global routing: {top_module} | "
            f"adjustment={config.adjustment} | "
            f"layers={config.min_layer}–{config.max_layer}"
        )

        # Copy DEF to output dir so Docker finds it at /work/
        dest_def = output_dir / def_path.name
        if def_path.resolve() != dest_def.resolve() and def_path.exists():
            import shutil
            shutil.copy2(def_path, dest_def)

        # Copy synthesized netlist for OpenROAD link_design
        netlist_candidates = [
            output_dir.parent / "02_synthesis" / f"{top_module}_synth.v",
            output_dir.parent.parent / "02_synthesis" / f"{top_module}_synth.v",
        ]
        import shutil
        for netlist_path in netlist_candidates:
            if netlist_path.exists():
                shutil.copy2(netlist_path, output_dir / f"{top_module}_synth.v")
                break

        tcl = self._generate_global_route_script(def_path, top_module, config)
        run = self.docker.run_script(
            script_content = tcl,
            script_name    = "global_route.tcl",
            work_dir       = output_dir,
            timeout        = 1800,
        )
        result.run_results.append(run)

        if not run.success:
            result.error_message = self._extract_error(run.combined_output())
            self.logger.error(f"Global routing failed: {result.error_message}")
            return result

        # Collect output files
        guide = output_dir / "route_guides.txt"
        gdef  = output_dir / "global_routed.def"
        rpt   = output_dir / "congestion.rpt"

        if guide.exists() and guide.stat().st_size > 50:
            result.guide_path = str(guide)
            result.success = True
        else:
            result.guide_path = None
            result.error_message = "route_guides.txt missing or empty."
            self.logger.error("Global Route validation failed: empty or missing route guides.")
            result.success = False
            
        if gdef.exists():
            content = gdef.read_text(encoding="utf-8", errors="ignore")
            if "COMPONENTS" in content:
                result.def_path = str(gdef)
            else:
                result.def_path = None
                result.success = False
                result.error_message = "global_routed.def appeared invalid."
        else:
            result.def_path = None

        result.report_path = str(rpt)   if rpt.exists()   else None

        if result.report_path:
            result.congestion = self._parse_congestion_report(
                Path(result.report_path)
            )

        if not result.success and not result.error_message:
            result.error_message = "Global routing validation failed."

        self.logger.info(
            f"Global routing {'complete' if result.success else 'FAILED'} | "
            f"overflow={result.congestion.overflow_count} tiles"
        )
        return result

    def check_congestion(
        self,
        def_path:   str | Path,
        top_module: str,
        output_dir: str | Path,
        config:     Optional[GlobalRouteConfig] = None,
    ) -> CongestionStats:
        """
        Run global routing and return congestion statistics only.
        Useful for checking whether a design is routable before committing
        to full detailed routing.

        Args:
            def_path:   Path to cts.def.
            top_module: Top module name.
            output_dir: Output directory.
            config:     Routing parameters.

        Returns:
            CongestionStats (does not require route_guides.txt to exist).
        """
        result = self.run(def_path, top_module, output_dir, config)
        return result.congestion

    # ──────────────────────────────────────────────────────────────────────
    # TCL GENERATOR
    # ──────────────────────────────────────────────────────────────────────

    def _generate_global_route_script(
        self,
        def_path:   Path,
        top_module: str,
        config:     GlobalRouteConfig,
    ) -> str:
        """
        Generate the FastRoute global routing Tcl script.

        Key commands:
          set_routing_layers        – constrain signal layers
          set_global_routing_layer_adjustment – per-layer capacity
          global_route              – run FastRoute
          write_guides              – output route_guides.txt
        """
        tech_lef = "/pdk/sky130A/libs.ref/sky130_fd_sc_hd/techlef/sky130_fd_sc_hd__nom.tlef"
        cell_lef = "/pdk/sky130A/libs.ref/sky130_fd_sc_hd/lef/sky130_fd_sc_hd.lef"
        lib_tt   = "/pdk/sky130A/libs.ref/sky130_fd_sc_hd/lib/sky130_fd_sc_hd__tt_025C_1v80.lib"

        # Build per-layer adjustment commands
        layer_adj_cmds = "\n".join(
            f"set_global_routing_layer_adjustment {layer} {frac}"
            for layer, frac in config.layer_adjustments.items()
        )

        return textwrap.dedent(f"""
        # ────────────────────────────────────────────────────────────────
        # Global Routing (FastRoute)  –  RTL-Gen AI
        # Top module  : {top_module}
        # Layers      : {config.min_layer} – {config.max_layer}
        # Adjustment  : {config.adjustment}
        # ────────────────────────────────────────────────────────────────

        # ── 1. Read PDK files ─────────────────────────────────────────
        read_lef     {tech_lef}
        read_lef     {cell_lef}
        read_liberty {lib_tt}

        # ── 2. Read netlist and post-CTS DEF ─────────────────────────
        catch {{ read_verilog /work/{top_module}_synth.v }}
        catch {{ link_design {top_module} }}
        read_def /work/{def_path.name}

        # ── 3. Clock constraint ───────────────────────────────────────
        create_clock -name {config.clock_net} \\
                     -period {config.clock_period_ns} \\
                     [get_ports {config.clock_net}]

        # ── 4. Set signal routing layer range ─────────────────────────
        # Note: SKip set_routing_layers to avoid li1 layer issues
        # FastRoute will handle layer selection during routing

        # ── 5. Per-layer capacity adjustments ─────────────────────────
        # Reserve capacity so the detail router has room to manoeuvre
        {layer_adj_cmds}

        # ── 6. Run FastRoute global routing ───────────────────────────
        # Default parameters: will generate route guides automatically
        global_route

        # ── 7. Write global-routed DEF checkpoint ─────────────────────
        write_def /work/global_routed.def

        puts "\\n✅  Global routing complete: {top_module}\\n"
        exit
        """).strip()

    # ──────────────────────────────────────────────────────────────────────
    # REPORT PARSING
    # ──────────────────────────────────────────────────────────────────────

    def _parse_congestion_report(self, rpt_path: Path) -> CongestionStats:
        """
        Parse congestion.rpt for overflow and congestion metrics.

        OpenROAD congestion report contains lines like:
          "Global routing congestion report"
          "Total overflow: N"
          "Max H congestion: X.XXX"
          "Max V congestion: X.XXX"
          "Wirelength: N"
        """
        stats = CongestionStats()
        if not rpt_path.exists():
            return stats

        try:
            text = rpt_path.read_text(encoding="utf-8", errors="ignore")
            congestions: List[float] = []

            for line in text.splitlines():
                s = line.strip()

                # Total overflow
                m = re.match(r"Total overflow\s*:\s*(\d+)", s)
                if m:
                    stats.overflow_count = int(m.group(1))

                # Max congestion values (horizontal or vertical)
                m2 = re.match(r"Max [HV] congestion\s*:\s*([\d.]+)", s)
                if m2:
                    congestions.append(float(m2.group(1)))

                # Average congestion
                m3 = re.match(r"Avg [HV] congestion\s*:\s*([\d.]+)", s)
                if m3:
                    stats.avg_congestion = max(
                        stats.avg_congestion, float(m3.group(1))
                    )

                # Wirelength
                m4 = re.match(r"Wirelength\s*:\s*([\d.]+)", s)
                if m4:
                    stats.wirelength_um = float(m4.group(1))

                # Also parse "N overflow" at start of line
                m5 = re.match(r"(\d+) overflow", s)
                if m5:
                    stats.overflow_count = max(
                        stats.overflow_count, int(m5.group(1))
                    )

            if congestions:
                stats.max_congestion = max(congestions)

        except OSError:
            pass

        return stats

    def suggest_adjustments(
        self,
        stats:  CongestionStats,
        config: GlobalRouteConfig,
    ) -> List[str]:
        """
        Suggest parameter changes when congestion is too high.

        High congestion (>0.9) means the detail router will likely fail.
        Returns a list of human-readable recommendations.

        Args:
            stats:  CongestionStats from a completed global route run.
            config: The config that was used.

        Returns:
            List of suggestion strings.
        """
        suggestions: List[str] = []

        if stats.overflow_count > 0:
            suggestions.append(
                f"Overflow in {stats.overflow_count} tile(s). "
                f"Increase die size by reducing target_utilization in FloorplannerConfig."
            )

        if stats.max_congestion > 0.9:
            suggestions.append(
                f"Max congestion {stats.max_congestion:.3f} is very high. "
                f"Reduce density_target in PlacementConfig to spread cells."
            )
        elif stats.max_congestion > 0.7:
            new_adj = min(0.5, config.adjustment + 0.1)
            suggestions.append(
                f"Moderate congestion {stats.max_congestion:.3f}. "
                f"Try increasing adjustment to {new_adj:.2f}."
            )

        if not suggestions:
            suggestions.append(
                f"Congestion looks acceptable "
                f"(max={stats.max_congestion:.3f}, overflow={stats.overflow_count}). "
                f"Proceed to detailed routing."
            )

        return suggestions

    @staticmethod
    def _extract_error(output: str) -> str:
        for line in output.splitlines():
            s = line.strip()
            if s.startswith(("[ERROR", "Error:", "ERROR:")):
                return s[:200]
        return "Global routing error (check run log)"
