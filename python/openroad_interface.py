"""
openroad_interface.py  –  OpenROAD Physical Design Flow (Docker-based)
======================================================================
Abstraction layer for OpenROAD tool via Docker container.
Handles:
  - Design synthesis → placement → routing → power/timing analysis
  - DEF/GDS file management
  - Constraint files (SDC, LEF)
  - Incremental flow control
  - Result parsing

Usage:
    from python.openroad_interface import OpenROADFlow
    flow = OpenROADFlow(pdk_root="C:/pdk", docker_image="efabless/openlane:latest")
    result = flow.run_flow(
        design_dir="C:/mydesign",
        design_name="fifo_8x16",
        top_module="fifo_top"
    )
    if result.success:
        print(flow.get_results())

Requires:
    - Docker Desktop (running)
    - OpenLane image pulled
    - Design files in proper structure
"""

from __future__ import annotations

import os
import sys
import json
import logging
import tempfile
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional
from datetime import datetime

# Try to import docker_manager from same package
try:
    from python.docker_manager import DockerManager, ContainerResult
except ImportError:
    from docker_manager import DockerManager, ContainerResult


# ──────────────────────────────────────────────────────────────────────────────
# ENUMERATIONS
# ──────────────────────────────────────────────────────────────────────────────

class FlowStage(Enum):
    """OpenROAD flow stages."""
    SYNTHESIS      = "syn"
    FLOORPLAN      = "flp"
    PLACEMENT      = "pla"
    CTS            = "cts"
    ROUTING        = "rt"
    POWER_ANALYSIS = "pwr"
    TIMING         = "tim"
    DRC_CHECK      = "drc"


class DesignMetricsUnit(Enum):
    """Units for design metrics."""
    MICRONS = "µm"
    NANOMETERS = "nm"
    MICROMETERS = "µm²"


# ──────────────────────────────────────────────────────────────────────────────
# DATA CLASSES
# ──────────────────────────────────────────────────────────────────────────────

@dataclass
class DesignMetrics:
    """Physical design metrics from each stage."""
    stage: FlowStage = FlowStage.SYNTHESIS
    timestamp: str = ""
    
    # Core metrics
    area_um2: float = 0.0
    power_mw: float = 0.0
    slack_ns: float = 0.0
    timing_path: str = ""
    
    # Placement
    wirelength_um: float = 0.0
    cell_count: int = 0
    
    # Routing
    routed_nets: int = 0
    total_nets: int = 0
    congestion_score: float = 0.0
    
    # Power
    leakage_mw: float = 0.0
    dynamic_mw: float = 0.0
    
    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = datetime.now().isoformat()


@dataclass
class OpenROADResult:
    """Result of OpenROAD flow execution."""
    success: bool = False
    stage_completed: Optional[FlowStage] = None
    output_dir: str = ""
    
    # Flow artifacts
    gds_file: str = ""
    def_file: str = ""
    netlist_file: str = ""
    
    # Results
    metrics: DesignMetrics = field(default_factory=DesignMetrics)
    docker_output: str = ""
    docker_error: str = ""
    exception: Optional[Exception] = None
    
    # Log file
    log_file: str = ""


# ──────────────────────────────────────────────────────────────────────────────
# OPENROAD FLOW MANAGER
# ──────────────────────────────────────────────────────────────────────────────

class OpenROADFlow:
    """
    Orchestrates complete physical design flow via OpenROAD/Docker.
    """

    def __init__(
        self,
        pdk_root: str,
        docker_image: str = "efabless/openlane:latest"
    ):
        self.logger = logging.getLogger(__name__)
        self.pdk_root = pdk_root
        self.docker_image = docker_image
        self.docker = DockerManager()
        self.last_result = None
        self.metrics_history: List[DesignMetrics] = []

    # ──────────────────────────────────────────────────────────────────────────
    # FLOW CONTROL
    # ──────────────────────────────────────────────────────────────────────────

    def run_flow(
        self,
        design_dir: str,
        design_name: str,
        top_module: str,
        clock_period_ns: float = 10.0,
        target_density: float = 0.7,
        stages: Optional[List[FlowStage]] = None,
    ) -> OpenROADResult:
        """
        Execute complete OpenROAD flow.
        
        Args:
            design_dir: Path to design directory (contains Verilog, constraints, etc)
            design_name: Name of design
            top_module: Top-level module name
            clock_period_ns: Target clock period
            target_density: Target placement density (0.0-1.0)
            stages: Stages to run (default: all)
        
        Returns: OpenROADResult with success status and metrics
        """
        result = OpenROADResult()

        if stages is None:
            stages = [
                FlowStage.SYNTHESIS,
                FlowStage.FLOORPLAN,
                FlowStage.PLACEMENT,
                FlowStage.CTS,
                FlowStage.ROUTING,
                FlowStage.POWER_ANALYSIS,
                FlowStage.TIMING,
            ]

        try:
            # Verify Docker is ready
            docker_status = self.docker.verify_installation()
            if not docker_status.running:
                raise RuntimeError("Docker is not running. Start Docker Desktop.")

            # Create temporary output directory
            result.output_dir = tempfile.mkdtemp(prefix="openroad_")
            
            # Create setup TCL script
            tcl_script = self._create_flow_script(
                design_dir=design_dir,
                design_name=design_name,
                top_module=top_module,
                clock_period=clock_period_ns,
                target_density=target_density,
                stages=stages,
            )

            # Write TCL to temp file
            script_file = os.path.join(result.output_dir, "flow.tcl")
            with open(script_file, "w") as f:
                f.write(tcl_script)

            # Run OpenROAD in Docker
            docker_result = self.docker.run_openroad(
                work_dir=result.output_dir,
                command=f"openroad /work/flow.tcl",
                env_vars={
                    "PDK_ROOT": self.docker.windows_to_docker_path(self.pdk_root),
                    "DESIGN_HOME": self.docker.windows_to_docker_path(design_dir),
                }
            )

            result.docker_output = docker_result.stdout
            result.docker_error = docker_result.stderr

            if docker_result.returncode == 0:
                result.success = True
                result.stage_completed = stages[-1] if stages else None
                
                # Try to parse results
                result.metrics = self._parse_metrics(result.output_dir)
                self.metrics_history.append(result.metrics)
            else:
                result.success = False
                result.exception = docker_result.exception

        except Exception as e:
            result.success = False
            result.exception = e
            self.logger.error(f"OpenROAD flow failed: {e}")

        self.last_result = result
        return result

    def _create_flow_script(
        self,
        design_dir: str,
        design_name: str,
        top_module: str,
        clock_period: float,
        target_density: float,
        stages: List[FlowStage],
    ) -> str:
        """Generate OpenROAD TCL script for the flow."""
        
        docker_design_dir = self.docker.windows_to_docker_path(design_dir)
        
        script = f"""
# OpenROAD Flow Script - Auto-generated
set design_name {design_name}
set top_module {top_module}
set clock_period {clock_period}
set target_density {target_density}

# Read design
read_verilog {docker_design_dir}/rtl/*.v
read_liberty ${{PDK_ROOT}}/sky130A/libs.ref/sky130_fd_sc_hd/lib/sky130_fd_sc_hd__tt_025C_1v80.lib

# Synthesis
synth -top {top_module}

# Floorplanning
init_floorplan -site sky130_fd_sc_hd

# Placement
place_cells

# CTS
clock_tree_synthesis -update_instances

# Routing
detailed_route

# Analysis
report_area
report_power
report_tns

# Export
write_def /work/output.def
write_gds /work/output.gds
"""
        return script

    def _parse_metrics(self, output_dir: str) -> DesignMetrics:
        """Parse OpenROAD output logs for metrics."""
        metrics = DesignMetrics(stage=FlowStage.ROUTING)
        
        # Try to read result files
        def_file = os.path.join(output_dir, "output.def")
        gds_file = os.path.join(output_dir, "output.gds")
        
        if os.path.exists(def_file):
            metrics.area_um2 = self._estimate_area_from_def(def_file)
        
        return metrics

    def _estimate_area_from_def(self, def_file: str) -> float:
        """Rough estimate of chip area from DEF file."""
        try:
            with open(def_file, "r") as f:
                content = f.read(1000)  # First 1KB
                # Look for DIEAREA line
                for line in content.split("\n"):
                    if "DIEAREA" in line:
                        # Extract coordinates
                        parts = line.split()
                        if len(parts) >= 5:
                            try:
                                x_max = float(parts[-3])
                                y_max = float(parts[-1])
                                area = (x_max / 1000) * (y_max / 1000)  # Convert DBU to µm
                                return area
                            except:
                                pass
        except:
            pass
        
        return 0.0

    # ──────────────────────────────────────────────────────────────────────────
    # RESULT ACCESS
    # ──────────────────────────────────────────────────────────────────────────

    def get_results(self) -> Dict:
        """Return last flow result as dictionary."""
        if not self.last_result:
            return {}
        
        return {
            "success": self.last_result.success,
            "stage": self.last_result.stage_completed.value if self.last_result.stage_completed else None,
            "output_dir": self.last_result.output_dir,
            "gds_file": self.last_result.gds_file,
            "def_file": self.last_result.def_file,
            "metrics": {
                "area_um2": self.last_result.metrics.area_um2,
                "power_mw": self.last_result.metrics.power_mw,
                "slack_ns": self.last_result.metrics.slack_ns,
            }
        }

    def print_results(self):
        """Print formatted flow results."""
        if not self.last_result:
            print("No results available")
            return

        result = self.last_result
        print("\n" + "="*70)
        print("  OpenROAD Flow Results")
        print("="*70)
        print(f"  Status          : {'✅ PASS' if result.success else '❌ FAIL'}")
        print(f"  Stage Completed : {result.stage_completed.value if result.stage_completed else 'N/A'}")
        print(f"  Output Dir      : {result.output_dir}")
        print(f"\n  Metrics:")
        print(f"    Area          : {result.metrics.area_um2:.2f} µm²")
        print(f"    Power         : {result.metrics.power_mw:.3f} mW")
        print(f"    Slack         : {result.metrics.slack_ns:.3f} ns")
        print(f"    Wirelength    : {result.metrics.wirelength_um:.1f} µm")
        if result.gds_file:
            print(f"\n  Outputs:")
            print(f"    GDS           : {result.gds_file}")
            print(f"    DEF           : {result.def_file}")
        print("="*70 + "\n")
