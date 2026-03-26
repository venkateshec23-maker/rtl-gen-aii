"""
placer.py  –  Standard Cell Placement for RTL-Gen AI
=====================================================
Runs OpenROAD's placement engine inside Docker to place all standard
cells from floorplan.def into legal, non-overlapping positions.

Placement stages
─────────────────
Stage 1 – Global Placement  (RePlAce)
    Minimises total wirelength by distributing cells across the core
    area.  Cells may overlap at this stage.  Fast (seconds).

Stage 2 – Legalisation  (OpenDP)
    Snaps every cell to a valid placement row and resolves all
    overlaps.  No wirelength optimisation.

Stage 3 – Detailed Placement  (OpenDP optimisations)
    Local moves (swaps, shifts) that reduce wirelength while keeping
    cells legal.  Run after legalisation.

Stage 4 – Placement quality check
    Verifies zero overlaps remain.  Reports HPWL (half-perimeter
    wirelength) and cell density statistics.

Data flow
──────────
  floorplan.def  →  placer.py  →  OpenROAD (Docker)  →  placed.def
                                                        placement.rpt

Usage example
──────────────
    from python.docker_manager import DockerManager
    from python.pdk_manager    import PDKManager
    from python.placer         import Placer, PlacementConfig

    dm  = DockerManager()
    pdk = PDKManager()
    pl  = Placer(docker=dm, pdk=pdk)

    result = pl.run(
        def_path   = r"C:\\project\\physical\\floorplan.def",
        top_module = "adder_8bit",
        output_dir = r"C:\\project\\physical",
    )
    print(result.summary())
    # Writes: placed.def, placement.rpt
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
class PlacementConfig:
    """
    Parameters for the placement step.

    Defaults are conservative and work for most simple Sky130 designs.
    Tune density_target if the router reports congestion after routing.
    """
    # Clock period (ns) for timing-driven placement optimisation
    clock_period_ns:  float = 10.0

    # Name of the clock net
    clock_net:        str   = "clk"

    # Target cell density for global placement (0.0–1.0).
    # Lower values → more spread out → easier routing, larger die.
    # Higher values → tighter → harder routing, smaller die.
    density_target:   float = 0.60

    # Padding around each cell in placement rows (in units of site width).
    # 1 = one site width of space around every cell.
    cell_padding:     int   = 1

    # Whether to run detailed placement after legalisation.
    # True = better quality, slightly slower.
    run_detailed:     bool  = True

    # Whether to run timing-driven global placement.
    # True = better timing, may increase wirelength.
    timing_driven:    bool  = True


@dataclass
class PlacementStats:
    """
    Quality metrics extracted from the placement report.
    All values are 0.0 when the report could not be parsed.
    """
    hpwl_um:          float = 0.0   # Half-perimeter wirelength (µm)
    cell_count:       int   = 0     # Number of placed instances
    utilization_pct:  float = 0.0   # Actual placement utilisation %
    overflow:         float = 0.0   # Global placement overflow (0 = perfect)
    worst_slack_ns:   float = 0.0   # WNS after placement (ns; negative = violated)


@dataclass
class PlacementResult:
    """Complete result from Placer.run()."""
    top_module:   str
    output_dir:   str
    success:      bool = False

    placed_def:   Optional[str] = None   # Path to placed.def
    report_path:  Optional[str] = None   # Path to placement.rpt
    stats:        PlacementStats = field(default_factory=PlacementStats)

    run_results:  List[RunResult] = field(default_factory=list)
    error_message: str = ""

    def summary(self) -> str:
        status = "✅  SUCCESS" if self.success else "❌  FAILED"
        s      = self.stats
        lines  = [
            "",
            "╔" + "═" * 56 + "╗",
            "║  Placement Result  –  RTL-Gen AI" + " " * 22 + "║",
            "╠" + "═" * 56 + "╣",
            f"║  Status       : {status:<39} ║",
            f"║  Top module   : {self.top_module:<39} ║",
        ]
        if self.success:
            lines += [
                "╠" + "─" * 56 + "╣",
                f"║  Cells placed : {s.cell_count:<39} ║",
                f"║  HPWL         : {s.hpwl_um:.1f} µm"
                + " " * max(0, 37 - len(f"{s.hpwl_um:.1f} µm")) + " ║",
                f"║  Utilisation  : {s.utilization_pct:.1f} %"
                + " " * max(0, 38 - len(f"{s.utilization_pct:.1f} %")) + " ║",
                f"║  Overflow     : {s.overflow:.4f}"
                + " " * max(0, 39 - len(f"{s.overflow:.4f}")) + " ║",
                f"║  WNS          : {s.worst_slack_ns:.3f} ns"
                + " " * max(0, 36 - len(f"{s.worst_slack_ns:.3f} ns")) + " ║",
            ]
        if self.placed_def:
            p = Path(self.placed_def).name
            lines.append(f"║  DEF file     : {p:<39} ║")
        if self.error_message:
            lines += [
                "╠" + "─" * 56 + "╣",
                f"║  Error        : {self.error_message[:39]:<39} ║",
            ]
        lines.append("╚" + "═" * 56 + "╝")
        return "\n".join(lines)


# ──────────────────────────────────────────────────────────────────────────────
# MAIN CLASS
# ──────────────────────────────────────────────────────────────────────────────

class Placer:
    """
    Runs OpenROAD's placement engine via Docker.

    Reads  : floorplan.def  (from Floorplanner)
    Writes : placed.def, placement.rpt
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
        config:     Optional[PlacementConfig] = None,
    ) -> PlacementResult:
        """
        Run global placement → legalisation → detailed placement.

        Args:
            def_path:   Path to floorplan.def on Windows.
            top_module: Top-level module name.
            output_dir: Windows output directory.  placed.def goes here.
            config:     Placement parameters.

        Returns:
            PlacementResult with placed.def path and quality stats.
        """
        config     = config or PlacementConfig()
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        def_path   = Path(def_path)

        result = PlacementResult(
            top_module = top_module,
            output_dir = str(output_dir),
        )

        self.logger.info(
            f"Placement: {top_module} | "
            f"density={config.density_target} | "
            f"clk={config.clock_period_ns}ns"
        )

        # Copy DEF to output_dir so Docker finds it at /work/
        dest_def = output_dir / def_path.name
        if def_path.resolve() != dest_def.resolve() and def_path.exists():
            import shutil
            shutil.copy2(def_path, dest_def)

        # Generate and run the placement Tcl script
        tcl = self._generate_placement_script(def_path, top_module, config)
        
        # Ensure Docker has PDK mount information
        self.docker.pdk_root = self.pdk
        
        run = self.docker.run_script(
            script_content = tcl,
            script_name    = "placement.tcl",
            work_dir       = output_dir,
            timeout        = 900,
        )
        result.run_results.append(run)

        if not run.success:
            result.error_message = self._extract_error(run.combined_output())
            self.logger.error(f"Placement Docker failed (exit={run.return_code})")
            self.logger.error(f"Docker stdout:\n{run.stdout}")
            self.logger.error(f"Docker stderr:\n{run.stderr}")
            self.logger.error(f"Error: {result.error_message}")
            return result

        # Collect output files
        placed_def = output_dir / "placed.def"
        rpt        = output_dir / "placement.rpt"

        result.placed_def  = str(placed_def) if placed_def.exists() else None
        result.report_path = str(rpt)        if rpt.exists()        else None
        result.success     = placed_def.exists()

        if result.report_path:
            result.stats = self._parse_report(Path(result.report_path))

        if not result.success:
            # Docker exited 0 but placed.def not created - log Docker output for debugging
            self.logger.warning(
                f"Placement Docker script ran but placed.def not created. "
                f"Docker exit={run.return_code} (0=success)"
            )
            if run.stdout.strip() or run.stderr.strip():
                self.logger.warning(f"Docker stdout:\n{run.stdout[:1000]}")
                self.logger.warning(f"Docker stderr:\n{run.stderr[:1000]}")
            result.error_message = "placed.def not created"

        self.logger.info(
            f"Placement {'complete' if result.success else 'FAILED'} | "
            f"HPWL={result.stats.hpwl_um:.0f} µm | "
            f"cells={result.stats.cell_count}"
        )
        return result

    def run_global_only(
        self,
        def_path:   str | Path,
        top_module: str,
        output_dir: str | Path,
        config:     Optional[PlacementConfig] = None,
    ) -> RunResult:
        """
        Run only global placement (no legalisation or detailed pass).
        Useful for quick density / wirelength checks.
        """
        config     = config or PlacementConfig()
        output_dir = Path(output_dir)
        tcl        = self._generate_global_only_script(
            Path(def_path), top_module, config
        )
        return self.docker.run_script(
            script_content = tcl,
            script_name    = "global_place.tcl",
            work_dir       = output_dir,
            timeout        = 300,
        )

    # ──────────────────────────────────────────────────────────────────────
    # TCL GENERATORS
    # ──────────────────────────────────────────────────────────────────────

    def _generate_placement_script(
        self,
        def_path:   Path,
        top_module: str,
        config:     PlacementConfig,
    ) -> str:
        """
        Full placement Tcl: global → legalise → detailed → report.
        Uses RePlAce for global, OpenDP for legalisation/detailed.
        """
        tech_lef = "/pdk/sky130A/libs.ref/sky130_fd_sc_hd/techlef/sky130_fd_sc_hd__nom.tlef"
        cell_lef = "/pdk/sky130A/libs.ref/sky130_fd_sc_hd/lef/sky130_fd_sc_hd.lef"
        lib_tt   = "/pdk/sky130A/libs.ref/sky130_fd_sc_hd/lib/sky130_fd_sc_hd__tt_025C_1v80.lib"
        lib_ss   = "/pdk/sky130A/libs.ref/sky130_fd_sc_hd/lib/sky130_fd_sc_hd__ss_100C_1v60.lib"

        detailed_cmd = (
            "\n# Stage 3 – Detailed placement\n"
            "detailed_placement\n"
            if config.run_detailed else ""
        )
        timing_flag = "-timing_driven" if config.timing_driven else ""

        return textwrap.dedent(f"""
        # ────────────────────────────────────────────────────────────────
        # Placement Script  –  RTL-Gen AI
        # Top module  : {top_module}
        # Density     : {config.density_target}
        # Clock       : {config.clock_net} @ {config.clock_period_ns} ns
        # ────────────────────────────────────────────────────────────────

        # ── 1. Read PDK files ─────────────────────────────────────────
        read_lef     {tech_lef}
        read_lef     {cell_lef}
        read_liberty {lib_tt}
        read_liberty {lib_ss}

        # ── 2. Read floorplan DEF ─────────────────────────────────────
        read_def /work/{def_path.name}
        link_design {top_module}

        # ── 3. Clock constraint ───────────────────────────────────────
        create_clock -name {config.clock_net} \\
                     -period {config.clock_period_ns} \\
                     [get_ports {config.clock_net}]

        # ── 4. Set cell padding (spacing around each instance) ────────
        set_placement_padding -global -left  {config.cell_padding} \\
                                      -right {config.cell_padding}

        # ── 5. Global placement (RePlAce) ─────────────────────────────
        # skip_initial_place = skip random init (faster convergence)
        global_placement {timing_flag} \\
            -density {config.density_target} \\
            -skip_initial_place

        # ── 6. Legalisation (OpenDP) ──────────────────────────────────
        # Resolves all cell overlaps; snaps to placement rows
        legalize_placement
        {detailed_cmd}
        # ── 7. Verify zero overlaps ───────────────────────────────────
        check_placement -verbose

        # ── 8. Reports ────────────────────────────────────────────────
        # Timing report after placement
        set_propagated_clock [all_clocks]
        report_checks -path_delay max -format full_clock > /work/placement.rpt
        report_wns >> /work/placement.rpt
        report_tns >> /work/placement.rpt

        # Density / HPWL report
        report_design_area >> /work/placement.rpt

        # ── 9. Write output DEF ───────────────────────────────────────
        write_def /work/placed.def

        puts "\\n✅  Placement complete: {top_module}\\n"
        exit
        """).strip()

    def _generate_global_only_script(
        self,
        def_path:   Path,
        top_module: str,
        config:     PlacementConfig,
    ) -> str:
        """Global placement only – no legalisation."""
        tech_lef = "/pdk/sky130A/libs.ref/sky130_fd_sc_hd/techlef/sky130_fd_sc_hd__nom.tlef"
        cell_lef = "/pdk/sky130A/libs.ref/sky130_fd_sc_hd/lef/sky130_fd_sc_hd.lef"
        lib_tt   = "/pdk/sky130A/libs.ref/sky130_fd_sc_hd/lib/sky130_fd_sc_hd__tt_025C_1v80.lib"

        return textwrap.dedent(f"""
        read_lef     {tech_lef}
        read_lef     {cell_lef}
        read_liberty {lib_tt}
        read_def /work/{def_path.name}
        link_design {top_module}
        create_clock -name {config.clock_net} -period {config.clock_period_ns} \\
                     [get_ports {config.clock_net}]
        global_placement -density {config.density_target} -skip_initial_place
        write_def /work/global_placed.def
        puts "Global placement complete"
        exit
        """).strip()

    # ──────────────────────────────────────────────────────────────────────
    # REPORT PARSING
    # ──────────────────────────────────────────────────────────────────────

    def _parse_report(self, rpt_path: Path) -> PlacementStats:
        """
        Extract PlacementStats from a placement.rpt file.

        OpenROAD report lines we look for:
          "Design area N u^2 M% utilization"
          "wns X.XX"
          "tns X.XX"
          "Placement Analysis"  (marks start of density section)
        """
        stats = PlacementStats()
        if not rpt_path.exists():
            return stats

        try:
            text = rpt_path.read_text(encoding="utf-8", errors="ignore")
            for line in text.splitlines():
                stripped = line.strip()

                # Utilisation: "Design area 5000 u^2 63% utilization"
                m = re.match(
                    r"Design area\s+([\d.]+)\s+u\^2\s+([\d.]+)%", stripped
                )
                if m:
                    stats.utilization_pct = float(m.group(2))

                # WNS
                if stripped.startswith("wns "):
                    try:
                        stats.worst_slack_ns = float(stripped.split()[1])
                    except (IndexError, ValueError):
                        pass

                # Cell count: "Number of instances: N"
                m2 = re.match(r"Number of instances\s*:\s*(\d+)", stripped)
                if m2:
                    stats.cell_count = int(m2.group(1))

                # HPWL: "HPWL: N.NN"
                m3 = re.match(r"HPWL\s*:\s*([\d.]+)", stripped)
                if m3:
                    stats.hpwl_um = float(m3.group(1))

                # Overflow: "Overflow: N.NNNN"
                m4 = re.match(r"Overflow\s*:\s*([\d.]+)", stripped)
                if m4:
                    stats.overflow = float(m4.group(1))

        except OSError:
            pass

        return stats

    @staticmethod
    def _extract_error(output: str) -> str:
        for line in output.splitlines():
            s = line.strip()
            if s.startswith(("[ERROR", "Error:", "ERROR:")):
                return s[:200]
        return "Placement error (check run log)"
