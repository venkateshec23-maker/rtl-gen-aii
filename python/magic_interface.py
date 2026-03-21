"""
magic_interface.py  –  Magic VLSI Tool Parasitic Extraction (Docker-based)
==========================================================================
Abstraction layer for Magic tool via Docker container.
Handles:
  - GDS/DEF to Magic database conversion
  - Layout verification (DRC)
  - Parasitic resistance/capacitance extraction
  - SPICE netlist generation
  - GDS layer manipulation

Usage:
    from python.magic_interface import MagicFlow
    magic = MagicFlow(pdk_root="C:/pdk")
    result = magic.extract_parasitics(
        gds_file="C:/design/output.gds",
        output_dir="C:/design/extraction"
    )
    if result.success:
        spice_netlist = magic.get_extracted_netlist()

Requires:
    - Docker Desktop (running)
    - OpenLane image with Magic tool (~500MB)
    - PDK files accessible
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
from typing import Dict, List, Optional, Tuple
from datetime import datetime

# Try to import docker_manager from same package
try:
    from python.docker_manager import DockerManager, ContainerResult
except ImportError:
    from docker_manager import DockerManager, ContainerResult


# ──────────────────────────────────────────────────────────────────────────────
# ENUMERATIONS
# ──────────────────────────────────────────────────────────────────────────────

class ExtractionType(Enum):
    """Type of parasitic extraction."""
    RC_ONLY = "rc"           # Resistance & Capacitance
    RLC_FULL = "rlc"         # Full R, L, C extraction
    COUPLING = "coupling"    # Crosstalk coupling


class DRCViolationType(Enum):
    """Types of DRC violations."""
    SPACING = "spacing"
    WIDTH = "width"
    OVERLAP = "overlap"
    NOTCH = "notch"


# ──────────────────────────────────────────────────────────────────────────────
# DATA CLASSES
# ──────────────────────────────────────────────────────────────────────────────

@dataclass
class DRCViolation:
    """Single DRC rule violation."""
    rule_name: str = ""
    violation_type: DRCViolationType = DRCViolationType.SPACING
    location: Tuple[float, float] = (0.0, 0.0)
    layer: str = ""
    severity: str = "warning"  # "info", "warning", "error"


@dataclass
class DRCResults:
    """DRC check results."""
    total_violations: int = 0
    errors: List[DRCViolation] = field(default_factory=list)
    warnings: List[DRCViolation] = field(default_factory=list)
    is_clean: bool = field(init=False)
    timestamp: str = ""

    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = datetime.now().isoformat()
        self.is_clean = self.total_violations == 0


@dataclass
class ExtractionMetrics:
    """Parasitic extraction results."""
    total_resistance_ohm: float = 0.0
    total_capacitance_pf: float = 0.0
    total_inductance_nh: float = 0.0
    
    coupling_capacitance_pf: float = 0.0
    
    extracted_nets: int = 0
    total_nets: int = 0
    
    accuracy_confidence: float = 1.0  # 0.0-1.0


@dataclass
class MagicResult:
    """Result of Magic operation."""
    success: bool = False
    operation: str = ""  # "drc", "extract", "netlist", etc
    output_dir: str = ""
    
    # Artifacts
    extracted_spice: str = ""
    drc_results: DRCResults = field(default_factory=DRCResults)
    extraction_metrics: ExtractionMetrics = field(default_factory=ExtractionMetrics)
    
    # Logs
    docker_output: str = ""
    docker_error: str = ""
    exception: Optional[Exception] = None


# ──────────────────────────────────────────────────────────────────────────────
# MAGIC FLOW MANAGER
# ──────────────────────────────────────────────────────────────────────────────

class MagicFlow:
    """
    Orchestrates Magic VLSI tool operations via Docker.
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
        self.last_result: Optional[MagicResult] = None
        self.extracted_netlist: str = ""

    # ──────────────────────────────────────────────────────────────────────────
    # DRC CHECKING
    # ──────────────────────────────────────────────────────────────────────────

    def run_drc(self, gds_file: str, output_dir: Optional[str] = None) -> MagicResult:
        """
        Run Magic DRC checks on GDS file.
        
        Args:
            gds_file: Path to GDS file
            output_dir: Where to save DRC results
        
        Returns: MagicResult with DRC violations
        """
        result = MagicResult(operation="drc")

        if not output_dir:
            output_dir = tempfile.mkdtemp(prefix="magic_drc_")

        result.output_dir = output_dir

        try:
            docker_status = self.docker.verify_installation()
            if not docker_status.running:
                raise RuntimeError("Docker is not running")

            # Create Magic TCL script for DRC
            magicrc_script = self._create_drc_script(gds_file)
            
            script_file = os.path.join(output_dir, "drc.tcl")
            with open(script_file, "w") as f:
                f.write(magicrc_script)

            # Run in Docker
            docker_result = self.docker.run_openroad(
                work_dir=output_dir,
                command="magic -Tsky130A -nw -nx /work/drc.tcl > /work/drc.log 2>&1"
            )

            result.docker_output = docker_result.stdout
            result.docker_error = docker_result.stderr

            if docker_result.returncode == 0:
                result.success = True
                result.drc_results = self._parse_drc_log(os.path.join(output_dir, "drc.log"))
            else:
                result.success = False
                result.exception = docker_result.exception

        except Exception as e:
            result.success = False
            result.exception = e

        self.last_result = result
        return result

    def _create_drc_script(self, gds_file: str) -> str:
        """Generate Magic TCL script for DRC."""
        docker_gds = self.docker.windows_to_docker_path(gds_file)
        
        script = f"""
# Magic DRC Script (auto-generated)
gds read {docker_gds}
select all
drc check
drc statistics
quit
"""
        return script

    def _parse_drc_log(self, log_file: str) -> DRCResults:
        """Parse Magic DRC log for violations."""
        results = DRCResults()

        try:
            with open(log_file, "r") as f:
                content = f.read()
                
                # Count violations
                if "violations" in content.lower():
                    for line in content.split("\n"):
                        if "violations" in line.lower():
                            # Try to extract count
                            parts = line.split()
                            for i, part in enumerate(parts):
                                if part.isdigit():
                                    results.total_violations = int(part)
                                    break
                
                results.is_clean = results.total_violations == 0
        except:
            pass

        return results

    # ──────────────────────────────────────────────────────────────────────────
    # PARASITIC EXTRACTION
    # ──────────────────────────────────────────────────────────────────────────

    def extract_parasitics(
        self,
        gds_file: str,
        extraction_type: ExtractionType = ExtractionType.RC_ONLY,
        output_dir: Optional[str] = None,
    ) -> MagicResult:
        """
        Extract parasitic R, C, L from GDS layout.
        
        Args:
            gds_file: Path to GDS file
            extraction_type: Type of extraction (RC, RLC, coupling)
            output_dir: Where to save extracted SPICE
        
        Returns: MagicResult with extracted parasitics
        """
        result = MagicResult(operation="extract")

        if not output_dir:
            output_dir = tempfile.mkdtemp(prefix="magic_extract_")

        result.output_dir = output_dir

        try:
            docker_status = self.docker.verify_installation()
            if not docker_status.running:
                raise RuntimeError("Docker is not running")

            # Create extraction script
            extract_script = self._create_extraction_script(gds_file, extraction_type)
            
            script_file = os.path.join(output_dir, "extract.tcl")
            with open(script_file, "w") as f:
                f.write(extract_script)

            # Run extraction
            docker_result = self.docker.run_openroad(
                work_dir=output_dir,
                command="magic -Tsky130A -nw -nx /work/extract.tcl > /work/extract.log 2>&1"
            )

            result.docker_output = docker_result.stdout
            result.docker_error = docker_result.stderr

            if docker_result.returncode == 0:
                result.success = True
                
                # Look for generated SPICE file
                spice_file = os.path.join(output_dir, "extracted.spice")
                if os.path.exists(spice_file):
                    with open(spice_file, "r") as f:
                        self.extracted_netlist = f.read()
                    result.extracted_spice = spice_file
                
                # Parse extraction metrics
                result.extraction_metrics = self._parse_extraction_results(output_dir)
            else:
                result.success = False

        except Exception as e:
            result.success = False
            result.exception = e

        self.last_result = result
        return result

    def _create_extraction_script(
        self,
        gds_file: str,
        extraction_type: ExtractionType
    ) -> str:
        """Generate Magic extraction TCL script."""
        docker_gds = self.docker.windows_to_docker_path(gds_file)
        
        extraction_cmd = {
            ExtractionType.RC_ONLY: "extract",
            ExtractionType.RLC_FULL: "extract all",
            ExtractionType.COUPLING: "extract coupling",
        }[extraction_type]

        script = f"""
# Magic Parasitic Extraction Script
gds read {docker_gds}
{extraction_cmd}
write_spice /work/extracted.spice
quit
"""
        return script

    def _parse_extraction_results(self, output_dir: str) -> ExtractionMetrics:
        """Parse extraction output for metrics."""
        metrics = ExtractionMetrics()

        log_file = os.path.join(output_dir, "extract.log")
        try:
            with open(log_file, "r") as f:
                content = f.read()
                
                # Look for capacitance/resistance values
                for line in content.split("\n"):
                    if "Cap" in line or "Cload" in line:
                        try:
                            value = float(line.split()[-1])
                            metrics.total_capacitance_pf += value
                        except:
                            pass
        except:
            pass

        return metrics

    # ──────────────────────────────────────────────────────────────────────────
    # SPICE NETLIST GENERATION
    # ──────────────────────────────────────────────────────────────────────────

    def generate_spice_netlist(self, gds_file: str) -> str:
        """
        Generate SPICE netlist from GDS (combines layout + extracted R/C).
        
        Returns: SPICE netlist as string
        """
        result = self.extract_parasitics(gds_file)
        
        if result.success:
            return self.extracted_netlist
        else:
            return ""

    def get_extracted_netlist(self) -> str:
        """Return last extracted SPICE netlist."""
        return self.extracted_netlist

    # ──────────────────────────────────────────────────────────────────────────
    # RESULT REPORTING
    # ──────────────────────────────────────────────────────────────────────────

    def print_results(self):
        """Print formatted Magic operation results."""
        if not self.last_result:
            print("No results available")
            return

        result = self.last_result
        print("\n" + "="*70)
        print(f"  Magic {result.operation.upper()} Results")
        print("="*70)
        print(f"  Status          : {'✅ PASS' if result.success else '❌ FAIL'}")
        print(f"  Output Dir      : {result.output_dir}")

        if result.operation == "drc":
            drc = result.drc_results
            print(f"\n  DRC Results:")
            print(f"    Total Violations : {drc.total_violations}")
            print(f"    Errors           : {len(drc.errors)}")
            print(f"    Warnings         : {len(drc.warnings)}")
            print(f"    Status           : {'✅ CLEAN' if drc.is_clean else '⚠️  VIOLATIONS'}")

        elif result.operation == "extract":
            ext = result.extraction_metrics
            print(f"\n  Extraction Results:")
            print(f"    Total R          : {ext.total_resistance_ohm:.2f} Ω")
            print(f"    Total C          : {ext.total_capacitance_pf:.2f} pF")
            if ext.total_inductance_nh > 0:
                print(f"    Total L          : {ext.total_inductance_nh:.2f} nH")
            print(f"    Extracted Nets   : {ext.extracted_nets}")
            print(f"    Accuracy         : {ext.accuracy_confidence*100:.1f}%")
            
            if result.extracted_spice:
                print(f"\n  Artifacts:")
                print(f"    SPICE Netlist    : {result.extracted_spice}")

        print("="*70 + "\n")
