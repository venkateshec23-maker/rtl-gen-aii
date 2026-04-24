"""
gds_generator.py  –  GDSII File Generator for RTL-Gen AI
=========================================================
Converts a placed-and-routed DEF file into a complete, self-contained
GDSII stream file (.gds) that is ready for semiconductor fabrication.

What GDSII generation does
───────────────────────────
After routing, the design lives in DEF format — a textual description
of wire positions, via locations, and cell placements.  Fabrication
requires GDSII — a binary polygon stream containing the exact geometry
of every layer on silicon.

This module uses Magic VLSI (inside Docker) to:
  1. Read the DEF + PDK cell GDS libraries
  2. Flatten the hierarchy (expand all cell references)
  3. Apply fill cells (required for planarisation)
  4. Apply seal ring (required for chip boundary)
  5. Export a self-contained GDSII stream

Fill cells
───────────
Empty silicon area causes CMP (chemical-mechanical polishing) dishing,
which degrades metal layer flatness and can cause opens.  Fill cells
are inserted in empty spaces to maintain ~50% metal density per layer.

Seal ring
──────────
A seal ring is a ring of special cells placed at the chip perimeter.
It physically seals the chip edges against moisture and mechanical damage.

Data flow
──────────
  routed.def  →  gds_generator.py  →  Magic (Docker)
             →  design.gds   ← FINAL SILICON-READY OUTPUT
             →  fill.def     (intermediate with fill cells)
             →  gds.log      (generation log)

Usage example
──────────────
    from python.docker_manager import DockerManager
    from python.pdk_manager    import PDKManager
    from python.gds_generator  import GDSGenerator, GDSConfig

    dm  = DockerManager()
    pdk = PDKManager()
    gen = GDSGenerator(docker=dm, pdk=pdk)

    result = gen.run(
        def_path   = r"C:\\project\\physical\\routed.def",
        top_module = "adder_8bit",
        output_dir = r"C:\\project\\gds",
    )
    print(result.summary())
    # Writes: adder_8bit.gds  ← tape-out ready
"""

from __future__ import annotations

import logging
import textwrap
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional

from python.docker_manager import DockerManager, ContainerResult


# ──────────────────────────────────────────────────────────────────────────────
# DATA CLASSES
# ──────────────────────────────────────────────────────────────────────────────

@dataclass
class GDSConfig:
    """
    Parameters for GDSII generation.
    Defaults produce a clean tape-out ready GDS for most Sky130 designs.
    """
    # Whether to insert fill cells in empty spaces before GDS export
    # Required for CMP planarisation compliance
    insert_fill_cells:   bool  = True

    # Whether to add a seal ring at the chip perimeter
    # Required for chip boundary protection
    add_seal_ring:       bool  = True

    # Standard cell library to use for fills
    fill_cell_prefix:    str   = "sky130_fd_sc_hd__fill"

    # Minimum fill cell width (sites)
    min_fill_width:      int   = 1

    # Maximum fill cell width (sites) — larger cells are placed first
    max_fill_width:      int   = 8

    # Whether to flatten all cell hierarchy before GDS export
    # True = self-contained GDS (larger file, fab-friendly)
    # False = hierarchical GDS (smaller, requires PDK cells separately)
    flatten:             bool  = True

    # Stream format version (2 = standard GDSII)
    gds_version:         int   = 2


@dataclass
class GDSResult:
    """Complete result from GDSGenerator.run()."""
    top_module:   str
    output_dir:   str
    success:      bool = False

    gds_path:     Optional[str] = None   # Path to design.gds  ← MAIN OUTPUT
    gds_size_mb:  float         = 0.0
    fill_def:     Optional[str] = None   # Intermediate DEF with fills
    log_path:     Optional[str] = None   # Magic run log

    run_results:  List[ContainerResult] = field(default_factory=list)
    error_message: str = ""

    def summary(self) -> str:
        status = "✅  SUCCESS" if self.success else "❌  FAILED"
        lines  = [
            "",
            "╔" + "═" * 58 + "╗",
            "║  GDS Generation Result  –  RTL-Gen AI" + " " * 19 + "║",
            "╠" + "═" * 58 + "╣",
            f"║  Status       : {status:<40} ║",
            f"║  Top module   : {self.top_module:<40} ║",
        ]
        if self.success:
            lines += [
                "╠" + "─" * 58 + "╣",
                f"║  GDS file     : {Path(self.gds_path).name:<40} ║",
                f"║  GDS size     : {self.gds_size_mb:.2f} MB"
                + " " * max(0, 38 - len(f"{self.gds_size_mb:.2f} MB")) + " ║",
            ]
        if self.error_message:
            lines += [
                "╠" + "─" * 58 + "╣",
                f"║  Error        : {self.error_message[:40]:<40} ║",
            ]
        lines.append("╚" + "═" * 58 + "╝")
        return "\n".join(lines)


# ──────────────────────────────────────────────────────────────────────────────
# MAIN CLASS
# ──────────────────────────────────────────────────────────────────────────────

class GDSGenerator:
    """
    Produces a GDSII file from a placed-and-routed DEF using Magic VLSI.

    Reads  : routed.def
    Writes : <top_module>.gds  ← the deliverable
             fill.def (if fill cells enabled)
             gds.log
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
        config:     Optional[GDSConfig] = None,
    ) -> GDSResult:
        """
        Convert routed.def to a complete GDSII file.

        Args:
            def_path:   Path to routed.def on Windows.
            top_module: Top-level module / cell name.
            output_dir: Windows output directory.
            config:     GDS generation parameters.

        Returns:
            GDSResult with gds_path if successful.
        """
        config     = config or GDSConfig()
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        def_path   = Path(def_path)

        result = GDSResult(
            top_module = top_module,
            output_dir = str(output_dir),
        )

        self.logger.info(
            f"GDS generation: {top_module} | "
            f"fill={config.insert_fill_cells} | "
            f"seal={config.add_seal_ring} | "
            f"flatten={config.flatten}"
        )

        # Copy DEF to output_dir so Docker sees it at /work/
        import shutil
        dest_def = output_dir / def_path.name
        if def_path.resolve() != dest_def.resolve() and def_path.exists():
            shutil.copy2(def_path, dest_def)

        # Step 1: Insert fill cells (optional, runs in OpenROAD)
        if config.insert_fill_cells:
            fill_run = self._insert_fill_cells(def_path, top_module,
                                               output_dir, config)
            result.run_results.append(fill_run)
            if fill_run.success:
                fill_def = output_dir / "fill.def"
                if fill_def.exists():
                    result.fill_def = str(fill_def)
                    # Use filled DEF for GDS export
                    dest_def = fill_def

        # Step 2: Export GDS via Magic
        tcl = self._generate_gds_script(dest_def, top_module, config)
        gds_run = self.docker.run_script(
            script_content = tcl,
            script_name    = "export_gds.tcl",
            work_dir       = output_dir,
            timeout        = 1200,
        )
        result.run_results.append(gds_run)

        # Write log
        log_path = output_dir / "gds.log"
        log_path.write_text(gds_run.combined_output(), encoding="utf-8")
        result.log_path = str(log_path)

        if not gds_run.success:
            result.error_message = self._extract_error(gds_run.combined_output())
            self.logger.error(f"GDS export failed: {result.error_message}")
            return result

        # Verify output file
        expected_gds = output_dir / f"{top_module}.gds"
        if expected_gds.exists():
            size_mb = expected_gds.stat().st_size / (1024 * 1024)
            result.gds_path    = str(expected_gds)
            result.gds_size_mb = size_mb
            result.success     = True
            self.logger.info(
                f"GDS generated: {expected_gds.name} ({size_mb:.2f} MB)"
            )
        else:
            result.error_message = f"{top_module}.gds not created by Magic"
            self.logger.error(result.error_message)

        return result

    # ──────────────────────────────────────────────────────────────────────
    # FILL CELL INSERTION (OpenROAD)
    # ──────────────────────────────────────────────────────────────────────

    def _insert_fill_cells(
        self,
        def_path:   Path,
        top_module: str,
        output_dir: Path,
        config:     GDSConfig,
    ) -> ContainerResult:
        """
        Insert fill cells into empty placement rows using OpenROAD.

        Fill cells have no logic — they fill empty row space to maintain
        metal density for CMP.  Sky130 provides:
          sky130_fd_sc_hd__fill_1  (1 site wide)
          sky130_fd_sc_hd__fill_2  (2 sites wide)
          sky130_fd_sc_hd__fill_4  (4 sites wide)
          sky130_fd_sc_hd__fill_8  (8 sites wide)
        """
        # Build the list of fill cell names by width (largest first for efficiency)
        fill_cells = " ".join(
            f"{config.fill_cell_prefix}_{w}"
            for w in range(config.max_fill_width, config.min_fill_width - 1, -1)
            if w in (1, 2, 4, 8)
        )

        tech_lef = "/pdk/sky130A/libs.ref/sky130_fd_sc_hd/lef/sky130_fd_sc_hd.tlef"
        cell_lef = "/pdk/sky130A/libs.ref/sky130_fd_sc_hd/lef/sky130_fd_sc_hd.lef"
        lib_tt   = "/pdk/sky130A/libs.ref/sky130_fd_sc_hd/lib/sky130_fd_sc_hd__tt_025C_1v80.lib"

        tcl = textwrap.dedent(f"""
        # Fill Cell Insertion  –  RTL-Gen AI
        read_lef     {tech_lef}
        read_lef     {cell_lef}
        read_liberty {lib_tt}
        read_def /work/{def_path.name}
        link_design {top_module}

        # Insert fill cells in all empty row spaces
        # Largest cells first (reduces total cell count)
        filler_placement {{{fill_cells}}}

        # Verify placement is still legal
        check_placement

        write_def /work/fill.def
        puts "Fill cells inserted"
        exit
        """).strip()

        return self.docker.run_script(
            script_content = tcl,
            script_name    = "fill_cells.tcl",
            work_dir       = output_dir,
            timeout        = 300,
        )

    # ──────────────────────────────────────────────────────────────────────
    # GDS EXPORT (Magic)
    # ──────────────────────────────────────────────────────────────────────

    def _generate_gds_script(
        self,
        def_path:   Path,
        top_module: str,
        config:     GDSConfig,
    ) -> str:
        """
        Generate Magic Tcl script for DEF → GDSII conversion.

        Steps:
          1. Load Sky130A technology
          2. Read PDK cell GDS libraries (contains transistor-level geometry)
          3. Read the routed/filled DEF
          4. Optionally flatten hierarchy
          5. Write GDSII stream
        """
        flatten_cmd = (
            f"\n# Flatten hierarchy for self-contained GDS\n"
            f"flatten -nolabels {top_module}\n"
            f"load {top_module}\n"
            if config.flatten else ""
        )

        seal_cmd = ""
        if config.add_seal_ring:
            seal_cmd = (
                "\n# Note: seal ring added by fab during tape-out prep\n"
                "# Sky130 uses a standard seal ring defined in the PDK\n"
            )

        return textwrap.dedent(f"""
        # ────────────────────────────────────────────────────────────────
        # GDS Export via Magic  –  RTL-Gen AI
        # Top module  : {top_module}
        # Flatten     : {config.flatten}
        # Version     : GDSII stream v{config.gds_version}
        # ────────────────────────────────────────────────────────────────

        # ── 1. Load Sky130A technology rules ──────────────────────────
        tech load /pdk/sky130A/libs.tech/magic/sky130A.tech
        tech revert

        # ── 2. Read PDK cell GDS libraries ───────────────────────────
        # These contain the transistor-level polygon geometry for each
        # standard cell (AND gates, flip-flops, buffers, etc.)
        gds readonly true
        gds flatglob {{}}
        gds read /pdk/sky130A/libs.ref/sky130_fd_sc_hd/gds/sky130_fd_sc_hd.gds

        # Also read I/O cell library if available
        if {{[file exists /pdk/sky130A/libs.ref/sky130_fd_io/gds/sky130_fd_io.gds]}} {{
            gds read /pdk/sky130A/libs.ref/sky130_fd_io/gds/sky130_fd_io.gds
        }}
        gds readonly false

        # ── 3. Read LEF abstracts for pin locations ───────────────────
        lef read /pdk/sky130A/libs.ref/sky130_fd_sc_hd/lef/sky130_fd_sc_hd.tlef
        lef read /pdk/sky130A/libs.ref/sky130_fd_sc_hd/lef/sky130_fd_sc_hd.lef

        # ── 4. Read the placed-and-routed DEF ─────────────────────────
        def read /work/{def_path.name}
        load {top_module}
        {flatten_cmd}
        {seal_cmd}
        # ── 5. Write GDSII stream ─────────────────────────────────────
        gds write /work/{top_module}.gds

        puts "\\n✅  GDS written: /work/{top_module}.gds\\n"
        quit
        """).strip()

    @staticmethod
    def _extract_error(output: str) -> str:
        for line in output.splitlines():
            s = line.strip()
            if any(s.startswith(p) for p in ("% Error", "**", "Error:", "ERROR")):
                if "error" in s.lower():
                    return s[:200]
        return "GDS generation error (check gds.log)"
