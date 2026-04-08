"""
floorplanner.py  –  Physical Design Floorplanning Orchestrator
=============================================================
Orchestrates die estimation, I/O placement, and power grid generation.
Runs complete floorplanning flow via OpenROAD/Docker.

Usage:
    from python.floorplanner import FloorplannerConfig, Floorplanner
    config = FloorplannerConfig(
        design_name="fifo_8x16",
        rtl_file="design.v",
        netlist_file="design_syn.v",
        target_util=0.70
    )
    flow = Floorplanner(config, pdk_root="C:/pdk")
    result = flow.run()
    print(result.floorplan_def)

Output: floorplan.def ready for placement
"""

from __future__ import annotations

import os
import sys
import tempfile
import logging
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Optional

# Import Phase 2 modules
sys.path.insert(0, os.path.dirname(__file__))

try:
    from python.die_estimator import DieEstimator
    from python.io_placer import IOPlacer
    from python.power_grid_generator import PowerGridGenerator
    from python.docker_manager import DockerManager
except ImportError:
    from die_estimator import DieEstimator
    from io_placer import IOPlacer
    from power_grid_generator import PowerGridGenerator
    from docker_manager import DockerManager


# ──────────────────────────────────────────────────────────────────────────────
# DATA CLASSES
# ──────────────────────────────────────────────────────────────────────────────

@dataclass
class FloorplannerConfig:
    """Configuration for floorplanning run."""
    design_name: str = ""
    rtl_file: str = ""
    netlist_file: str = ""
    
    # Flow parameters
    target_util: float = 0.70
    square_die: bool = True
    
    # Power/ground pins
    power_pin: str = "VDD"
    ground_pin: str = "VSS"
    
    # Output
    output_dir: str = ""
    
    def __post_init__(self):
        if not self.output_dir:
            self.output_dir = tempfile.mkdtemp(prefix="floorplan_")


@dataclass
class FloorplanResult:
    """Result of floorplanning."""
    success: bool = False
    design_name: str = ""
    
    # Outputs
    floorplan_def: str = ""
    floorplan_tcl: str = ""
    
    # Metrics
    die_width_um: float = 0.0
    die_height_um: float = 0.0
    core_width_um: float = 0.0
    core_height_um: float = 0.0
    
    # Logs
    docker_output: str = ""
    error_message: str = ""


# ──────────────────────────────────────────────────────────────────────────────
# FLOORPLANNER ORCHESTRATOR
# ──────────────────────────────────────────────────────────────────────────────

class Floorplanner:
    """
    Orchestrates complete floorplanning flow.
    """
    
    def __init__(
        self,
        config: FloorplannerConfig,
        pdk_root: str = "C:\\pdk",
        docker_image: str = "efabless/openlane:2024.02"
    ):
        self.config = config
        self.pdk_root = pdk_root
        self.docker_image = docker_image
        self.logger = logging.getLogger(__name__)
        
        self.docker = DockerManager()
        self.estimator = DieEstimator()
        
        self.result = FloorplanResult(design_name=config.design_name)
    
    def _estimate_cell_count(self, netlist_path: str) -> int:
        """Estimate number of cells in the synthesized netlist."""
        try:
            if isinstance(netlist_path, str):
                netlist_path = Path(netlist_path)
            else:
                netlist_path = Path(netlist_path)
            
            if not netlist_path.exists():
                self.logger.warning(f"Netlist not found for cell count estimate: {netlist_path}")
                return 1000  # Conservative default
            
            content = netlist_path.read_text(encoding="utf-8", errors="ignore")
            # Count instantiations (look for instance names like sky130_fd_sc_hd__*)
            cell_count = content.count("sky130_fd_sc_hd__")
            
            if cell_count == 0:
                # Fallback: count module instantiations
                cell_count = content.count("(") // 2  # rough estimate
            
            if cell_count < 10:
                cell_count = 100  # Minimum estimate
            
            self.logger.info(f"Estimated cell count: {cell_count}")
            return cell_count
            
        except Exception as e:
            self.logger.warning(f"Cell count estimation failed: {e}, using default 1000")
            return 1000
    
    # ──────────────────────────────────────────────────────────────────────────
    # MAIN FLOW
    # ──────────────────────────────────────────────────────────────────────────
    
    def run(self) -> FloorplanResult:
        """Execute complete floorplanning flow."""
        try:
            # Step 1: Dies size estimation
            die_est = self.estimator.estimate_from_netlist(
                self.config.netlist_file,
                target_util=self.config.target_util,
                square_die=self.config.square_die
            )
            
            self.result.die_width_um = die_est.die_width_um
            self.result.die_height_um = die_est.die_height_um
            self.result.core_width_um = die_est.core_width_um
            self.result.core_height_um = die_est.core_height_um
            
            # Step 2: Explicit IO pin placement on correct SKY130 layers
            # SKY130 layer directions: met3=horizontal, met4=vertical
            # make_tracks (in TCL) must be called first to populate routing DB.
            io_tcl = "place_pins -hor_layers met3 -ver_layers met4"
            
            # Step 3: Tapcell insertion instead of full old-style PDN
            pdn_tcl = "tapcell -distance 14 -tapcell_master sky130_fd_sc_hd__tapvpwrvgnd_1"
            
            # Step 4: Create complete TCL script
            complete_tcl = self._create_floorplan_tcl(
                die_est,
                io_tcl,
                pdn_tcl
            )
            
            # Step 5: Run OpenROAD via Docker
            result = self._run_floorplan_docker(complete_tcl)
            
            if result:
                self.result.success = True
                self.result.floorplan_def = result
            else:
                self.result.error_message = "Docker execution failed"
        
        except Exception as e:
            self.result.success = False
            self.result.error_message = str(e)
            self.logger.error(f"Floorplanning failed: {e}")
        
        return self.result
    
    def _create_floorplan_tcl(self, die_est, io_tcl: str, pdn_tcl: str) -> str:
        """Assemble complete floorplanning TCL script."""
        
        tech_lef = "/pdk/sky130A/libs.ref/sky130_fd_sc_hd/techlef/sky130_fd_sc_hd__nom.tlef"
        cell_lef = "/pdk/sky130A/libs.ref/sky130_fd_sc_hd/lef/sky130_fd_sc_hd.lef"
        lib_tt   = "/pdk/sky130A/libs.ref/sky130_fd_sc_hd/lib/sky130_fd_sc_hd__tt_025C_1v80.lib"
        lib_ss   = "/pdk/sky130A/libs.ref/sky130_fd_sc_hd/lib/sky130_fd_sc_hd__ss_100C_1v60.lib"

        # SKY130 site pitch constraints:
        #   unithd row height = 2.72 um  (Y-snap)
        #   site width        = 0.46 um  (X-snap)
        # Core margin must be a multiple of these pitches.
        # We use 10.12 um (22 * 0.46)  and 10.88 um (4 * 2.72)
        # Minimum core: at least 4 rows x 20 sites = 10.88 um H x 9.2 um W
        die_w  = max(die_est.die_width_um,  80.0)
        die_h  = max(die_est.die_height_um, 60.0)
        core_x1 = 10.12
        core_y1 = 10.88
        core_x2 = die_w - 10.12
        core_y2 = die_h - 10.88

        # SKY130 layer directions (from tech LEF):
        #   met1 = horizontal tracks, pitch 0.34 um
        #   met2 = vertical   tracks, pitch 0.46 um
        #   met3 = horizontal tracks, pitch 0.68 um
        #   met4 = vertical   tracks, pitch 0.92 um
        #   met5 = horizontal tracks, pitch 3.40 um
        # IO pins: use met3 (H) and met4 (V) — wide enough pitch for IO pads

        tcl_script = f"""# Floorplanning Configuration - Auto-generated by RTL-Gen AI
set design_name {self.config.design_name}

# Load PDK Data
read_lef {tech_lef}
read_lef {cell_lef}
read_liberty {lib_tt}
read_liberty {lib_ss}

# Read synthesized netlist and link design
read_verilog /work/design_syn.v
link_design {self.config.design_name}

# Initialize floorplan with site-pitch-snapped margins
# die: {die_w:.2f} x {die_h:.2f} um
# core: {core_x1:.2f},{core_y1:.2f} -> {core_x2:.2f},{core_y2:.2f} um
initialize_floorplan -site unithd \\
    -die_area  "0 0 {die_w:.2f} {die_h:.2f}" \\
    -core_area "{core_x1:.2f} {core_y1:.2f} {core_x2:.2f} {core_y2:.2f}"

# CRITICAL: populate routing track database from tech LEF
# Without make_tracks, place_pins fails with "routing tracks not found" on every layer.
make_tracks

# Place IO pins: met3 = horizontal, met4 = vertical (SKY130 layer directions)
{io_tcl}

# Insert tapcells for latch-up prevention
{pdn_tcl}

# Write floorplan DEF
write_def /work/floorplan.def

"""
        return tcl_script

    
    def _run_floorplan_docker(self, tcl_script: str) -> Optional[str]:
        """Run floorplanning via Docker."""
        try:
            # Ensure output directory exists
            os.makedirs(self.config.output_dir, exist_ok=True)
            
            # Copy netlist
            netlist_dest = os.path.join(self.config.output_dir, "design_syn.v")
            if os.path.exists(self.config.netlist_file):
                with open(self.config.netlist_file, "r") as src:
                    with open(netlist_dest, "w") as dst:
                        dst.write(src.read())
                self.logger.debug(f"Copied netlist to {netlist_dest}")
            
            # Save TCL script for debugging
            self.logger.debug(f"Floorplan TCL script:\n{tcl_script}")
            
            # Run OpenROAD using run_script to properly mount and execute
            self.docker.pdk_root = self.pdk_root  # Ensure PDK is mounted
            
            run_result = self.docker.run_script(
                script_content=tcl_script,
                script_name="floorplan.tcl",
                work_dir=self.config.output_dir,
                timeout=600
            )
            
            if not run_result.success:
                self.result.error_message = f"Docker execution failed: {run_result.stderr[:200]}"
                self.logger.error(f"OpenROAD Floorplan failed:\n{run_result.combined_output()}")
                return None
                
            out_path = os.path.join(self.config.output_dir, "floorplan.def")
            if not os.path.exists(out_path):
                self.result.error_message = "floorplan.def was not created by OpenROAD."
                self.logger.error("floorplan.def missing after successful Docker execution.")
                return None
                
            # Verify DEF is non-empty and has COMPONENTS
            with open(out_path, "r", encoding="utf-8") as f:
                content = f.read()
                if "COMPONENTS" not in content or "UNITS" not in content:
                    self.result.error_message = "Generated floorplan.def is empty or malformed."
                    self.logger.error(self.result.error_message)
                    return None
            
            # NOTE: _add_pin_layer_geometry is DISABLED.
            # place_pins already writes complete PORT + LAYER + PLACED blocks.
            # Post-processing them corrupts the DEF (inserts premature semicolon
            # after line 1 of multi-line PORT blocks -> ODB-0421 parse error).
                    
            self.result.docker_output = run_result.combined_output()
            return out_path
            
        except Exception as e:
            self.result.error_message = str(e)
            self.logger.error(f"Floorplanner execution error: {e}")
            return None
    
    def _add_pin_layer_geometry(self, def_path: str) -> None:
        """
        DISABLED: place_pins now generates correct PORT+LAYER+PLACED blocks.
        Post-processing those blocks corrupts valid multi-line DEF syntax.
        Keeping the method stub to avoid AttributeError if called externally.
        """
        self.logger.debug("_add_pin_layer_geometry: skipped (place_pins output is complete)")

    
    # ──────────────────────────────────────────────────────────────────────────
    # RESULT REPORTING
    # ──────────────────────────────────────────────────────────────────────────
    
    def print_result(self):
        """Print formatted floorplanning result."""
        print("\n" + "="*70)
        print("  Floorplanning Results  –  RTL-Gen AI")
        print("="*70)
        print(f"  Design      : {self.result.design_name}")
        print(f"  Status      : {'✅ SUCCESS' if self.result.success else '❌ FAILED'}")
        
        if self.result.success:
            print(f"\n  Die Dimensions:")
            print(f"    Width   : {self.result.die_width_um:.0f} µm")
            print(f"    Height  : {self.result.die_height_um:.0f} µm")
            print(f"    Area    : {self.result.die_width_um * self.result.die_height_um:.0f} µm²")
            
            print(f"\n  Core Area:")
            print(f"    Width   : {self.result.core_width_um:.0f} µm")
            print(f"    Height  : {self.result.core_height_um:.0f} µm")
            print(f"    Area    : {self.result.core_width_um * self.result.core_height_um:.0f} µm²")
            
            if self.result.floorplan_def:
                print(f"\n  Output:")
                print(f"    DEF file generated ({len(self.result.floorplan_def)} chars)")
        else:
            print(f"  Error: {self.result.error_message}")
        
        print("="*70 + "\n")
