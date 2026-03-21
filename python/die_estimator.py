"""
die_estimator.py  –  Die Size & Core Area Estimator (Sky130)
============================================================
Parses Yosys synthesized netlists, counts cell instances from Sky130 library,
and calculates required die dimensions based on target utilization.

Usage:
    from python.die_estimator import DieEstimator
    estimator = DieEstimator()
    result = estimator.estimate_from_netlist(
        netlist_file="C:/design/design.v",
        target_util=0.70
    )
    print(f"Die: {result.die_width} x {result.die_height} µm")
    print(f"Core: {result.core_width} x {result.core_height} µm")

Output: FloorplanConfig with die/core dimensions for Floorplanner
"""

from __future__ import annotations

import re
import logging
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, Tuple


# ──────────────────────────────────────────────────────────────────────────────
# SKY130 STANDARD CELL LIBRARY
# ──────────────────────────────────────────────────────────────────────────────

# Sky130 HD cell areas (µm²) — subset of most common cells
SKY130_CELL_AREAS = {
    "sky130_fd_sc_hd__a2bb2o_1": 14.27,
    "sky130_fd_sc_hd__a2bb2o_2": 14.27,
    "sky130_fd_sc_hd__a2bb2o_4": 21.40,
    "sky130_fd_sc_hd__a21ao_1": 14.27,
    "sky130_fd_sc_hd__a21ao_2": 14.27,
    "sky130_fd_sc_hd__a21bai_1": 14.27,
    "sky130_fd_sc_hd__a21bai_2": 14.27,
    "sky130_fd_sc_hd__a21oi_1": 14.27,
    "sky130_fd_sc_hd__a21oi_2": 14.27,
    "sky130_fd_sc_hd__a22o_1": 14.27,
    "sky130_fd_sc_hd__a22oi_1": 14.27,
    "sky130_fd_sc_hd__a22oi_2": 14.27,
    "sky130_fd_sc_hd__a2o_1": 14.27,
    "sky130_fd_sc_hd__a2o_2": 14.27,
    "sky130_fd_sc_hd__a311o_1": 14.27,
    "sky130_fd_sc_hd__a311oi_1": 14.27,
    "sky130_fd_sc_hd__a311oi_2": 14.27,
    "sky130_fd_sc_hd__a31o_1": 14.27,
    "sky130_fd_sc_hd__a31o_2": 14.27,
    "sky130_fd_sc_hd__a31oi_1": 14.27,
    "sky130_fd_sc_hd__a31oi_2": 14.27,
    "sky130_fd_sc_hd__a32o_1": 14.27,
    "sky130_fd_sc_hd__a32o_2": 14.27,
    "sky130_fd_sc_hd__a32oi_1": 14.27,
    "sky130_fd_sc_hd__a32oi_2": 14.27,
    "sky130_fd_sc_hd__a41o_1": 14.27,
    "sky130_fd_sc_hd__a41o_2": 14.27,
    "sky130_fd_sc_hd__a41oi_1": 14.27,
    "sky130_fd_sc_hd__a41oi_2": 14.27,
    "sky130_fd_sc_hd__aoi21_1": 14.27,
    "sky130_fd_sc_hd__aoi21_2": 14.27,
    "sky130_fd_sc_hd__aoi211_1": 14.27,
    "sky130_fd_sc_hd__aoi211_2": 14.27,
    "sky130_fd_sc_hd__aoi22_1": 14.27,
    "sky130_fd_sc_hd__aoi22_2": 14.27,
    "sky130_fd_sc_hd__buf_1": 7.13,
    "sky130_fd_sc_hd__buf_2": 7.13,
    "sky130_fd_sc_hd__buf_4": 10.70,
    "sky130_fd_sc_hd__buf_6": 14.27,
    "sky130_fd_sc_hd__buf_8": 17.84,
    "sky130_fd_sc_hd__buf_12": 25.12,
    "sky130_fd_sc_hd__buf_16": 35.82,
    "sky130_fd_sc_hd__d_sr_latch_1": 35.82,
    "sky130_fd_sc_hd__dfbbn_1": 42.96,
    "sky130_fd_sc_hd__dfbbn_2": 42.96,
    "sky130_fd_sc_hd__dfbbp_1": 42.96,
    "sky130_fd_sc_hd__dfbbp_2": 42.96,
    "sky130_fd_sc_hd__dfrtp_1": 42.96,
    "sky130_fd_sc_hd__dfrtp_2": 42.96,
    "sky130_fd_sc_hd__inv_1": 7.13,
    "sky130_fd_sc_hd__inv_2": 7.13,
    "sky130_fd_sc_hd__inv_4": 10.70,
    "sky130_fd_sc_hd__inv_6": 14.27,
    "sky130_fd_sc_hd__inv_8": 17.84,
    "sky130_fd_sc_hd__inv_12": 25.12,
    "sky130_fd_sc_hd__inv_16": 35.82,
    "sky130_fd_sc_hd__mux2_1": 14.27,
    "sky130_fd_sc_hd__mux2_2": 14.27,
    "sky130_fd_sc_hd__mux4_1": 28.54,
    "sky130_fd_sc_hd__nand2_1": 7.13,
    "sky130_fd_sc_hd__nand2_2": 7.13,
    "sky130_fd_sc_hd__nand3_1": 10.70,
    "sky130_fd_sc_hd__nand3_2": 10.70,
    "sky130_fd_sc_hd__nand4_1": 14.27,
    "sky130_fd_sc_hd__nand4_2": 14.27,
    "sky130_fd_sc_hd__nor2_1": 7.13,
    "sky130_fd_sc_hd__nor2_2": 7.13,
    "sky130_fd_sc_hd__nor3_1": 10.70,
    "sky130_fd_sc_hd__nor3_2": 10.70,
    "sky130_fd_sc_hd__nor4_1": 14.27,
    "sky130_fd_sc_hd__nor4_2": 14.27,
    "sky130_fd_sc_hd__o21a_1": 14.27,
    "sky130_fd_sc_hd__o21a_2": 14.27,
    "sky130_fd_sc_hd__o21ai_1": 14.27,
    "sky130_fd_sc_hd__o21ai_2": 14.27,
    "sky130_fd_sc_hd__o2bb2o_1": 14.27,
    "sky130_fd_sc_hd__o2bb2o_2": 14.27,
    "sky130_fd_sc_hd__o2bb2o_4": 21.40,
    "sky130_fd_sc_hd__o311a_1": 14.27,
    "sky130_fd_sc_hd__o311a_2": 14.27,
    "sky130_fd_sc_hd__o31a_1": 14.27,
    "sky130_fd_sc_hd__o31a_2": 14.27,
    "sky130_fd_sc_hd__o32a_1": 14.27,
    "sky130_fd_sc_hd__o32a_2": 14.27,
    "sky130_fd_sc_hd__oai21_1": 14.27,
    "sky130_fd_sc_hd__oai21_2": 14.27,
    "sky130_fd_sc_hd__oai211_1": 14.27,
    "sky130_fd_sc_hd__oai211_2": 14.27,
    "sky130_fd_sc_hd__oai22_1": 14.27,
    "sky130_fd_sc_hd__oai22_2": 14.27,
}


# ──────────────────────────────────────────────────────────────────────────────
# DATA CLASSES
# ──────────────────────────────────────────────────────────────────────────────

@dataclass
class DieEstimate:
    """Estimated die and core dimensions."""
    total_cell_area_um2: float = 0.0
    cell_count: int = 0
    unique_cell_types: int = 0
    
    # Core area
    core_area_um2: float = 0.0
    core_width_um: float = 0.0
    core_height_um: float = 0.0
    
    # Die area (core + margin)
    die_width_um: float = 0.0
    die_height_um: float = 0.0
    
    # Metrics
    target_utilization: float = 0.70
    actual_utilization: float = 0.0
    
    # Cell breakdown
    cell_count_by_type: Dict[str, int] = None
    
    def __post_init__(self):
        if self.cell_count_by_type is None:
            self.cell_count_by_type = {}


# ──────────────────────────────────────────────────────────────────────────────
# DIE ESTIMATOR
# ──────────────────────────────────────────────────────────────────────────────

class DieEstimator:
    """Estimates die size from synthesized netlist."""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.margin_percent = 15  # 15% margin for routing/power
    
    def estimate_from_netlist(
        self,
        netlist_file: str,
        target_util: float = 0.70,
        square_die: bool = True
    ) -> DieEstimate:
        """
        Estimate die size from Verilog netlist.
        
        Args:
            netlist_file: Path to synthesized Verilog
            target_util: Target utilization (0.0-1.0)
            square_die: Force square die (W ≈ H)
        
        Returns: DieEstimate with dimensions
        """
        estimate = DieEstimate(target_utilization=target_util)
        
        try:
            # Parse netlist
            cell_instances = self._parse_netlist(netlist_file)
            
            # If no cell instances found, try parsing from behavioral operators (fallback)
            if not cell_instances:
                self.logger.warning("No gate-level cells found. Estimating from behavioral operators.")
                cell_instances = self._estimate_from_behavioral_verilog(netlist_file)
            
            # Sum cell areas
            total_area = 0.0
            unique_types = set()
            
            for cell_type, count in cell_instances.items():
                area = SKY130_CELL_AREAS.get(cell_type, 14.27)  # Default 1-track area
                total_area += area * count
                estimate.cell_count_by_type[cell_type] = count
                unique_types.add(cell_type)
            
            estimate.total_cell_area_um2 = total_area
            estimate.cell_count = sum(cell_instances.values())
            estimate.unique_cell_types = len(unique_types)
            
            # Calculate core area (with utilization)
            estimate.core_area_um2 = total_area / target_util
            
            # Calculate dimensions
            if square_die:
                side = estimate.core_area_um2 ** 0.5
                estimate.core_width_um = side
                estimate.core_height_um = side
            else:
                # Aspect ratio ~1.4 (common for ASICs)
                estimate.core_height_um = (estimate.core_area_um2 / 1.4) ** 0.5
                estimate.core_width_um = 1.4 * estimate.core_height_um
            
            # Add margin for routing and power
            margin_factor = 1.0 + (self.margin_percent / 100.0)
            estimate.die_width_um = estimate.core_width_um * margin_factor
            estimate.die_height_um = estimate.core_height_um * margin_factor
            
            # Round to nearest 10 µm
            estimate.die_width_um = round(estimate.die_width_um / 10) * 10
            estimate.die_height_um = round(estimate.die_height_um / 10) * 10
            
            # Actual utilization
            die_area = estimate.die_width_um * estimate.die_height_um
            estimate.actual_utilization = estimate.total_cell_area_um2 / die_area if die_area > 0 else 0
            
        except Exception as e:
            self.logger.error(f"Estimation failed: {e}")
        
        return estimate
    
    def _parse_netlist(self, netlist_file: str) -> Dict[str, int]:
        """Parse Verilog netlist and count cell instances."""
        cell_counts = {}
        
        try:
            with open(netlist_file, "r") as f:
                content = f.read()
            
            # Pattern: sky130_fd_sc_hd__xxx_n instance_name (...)
            pattern = r"(sky130_fd_sc_hd__\w+)\s+\w+\s*\("
            matches = re.findall(pattern, content)
            
            for match in matches:
                cell_counts[match] = cell_counts.get(match, 0) + 1
        
        except Exception as e:
            self.logger.error(f"Failed to parse netlist: {e}")
        
        return cell_counts
    
    def _estimate_from_behavioral_verilog(self, netlist_file: str) -> Dict[str, int]:
        """
        Estimate cell count from behavioral Verilog (no gate-level cells).
        Counts operators and estimates equivalent cell count.
        """
        cell_counts = {}
        try:
            with open(netlist_file, "r") as f:
                content = f.read()
            
            # Count various operators and logic constructs
            # Each operator roughly maps to 1-2 library cells
            assign_count = len(re.findall(r"assign\s+", content))
            and_ops = len(re.findall(r"&(?!=)", content))
            or_ops = len(re.findall(r"\|(?!=)", content))
            xor_ops = len(re.findall(r"\^", content))
            not_ops = len(re.findall(r"~", content))
            dff_count = len(re.findall(r"always\s+@\s*\(\s*posedge", content))
            
            # Map behavioral constructs to equivalent SKY130 cells
            # This is approximate - basic gate equivalents
            cell_counts["sky130_fd_sc_hd__inv"] = int(not_ops * 0.5)  # NOT gates
            cell_counts["sky130_fd_sc_hd__and2"] = int(and_ops * 0.3)  # AND gates
            cell_counts["sky130_fd_sc_hd__or2"] = int(or_ops  * 0.3)   # OR gates
            cell_counts["sky130_fd_sc_hd__xor2"] = int(xor_ops * 0.4)  # XOR gates
            cell_counts["sky130_fd_sc_hd__dff"] = int(dff_count * 3)   # DFF cells (~3 per always block)
            
            # Add some baseline cells for logic glue
            total_ops = assign_count + and_ops + or_ops + xor_ops + not_ops + dff_count
            if total_ops > 0:
                cell_counts["sky130_fd_sc_hd__and2"] = max(10, int(total_ops * 0.5))
            
            self.logger.info(f"Estimated {sum(cell_counts.values())} cells from behavioral Verilog")
        
        except Exception as e:
            self.logger.error(f"Failed to estimate from behavioral Verilog: {e}")
        
        return cell_counts
    
    def print_estimate(self, estimate: DieEstimate):
        """Print formatted estimate."""
        print("\n" + "="*70)
        print("  Die Size Estimation  –  RTL-Gen AI")
        print("="*70)
        print(f"  Cells     : {estimate.cell_count} instances ({estimate.unique_cell_types} types)")
        print(f"  Cell Area : {estimate.total_cell_area_um2:.0f} µm²")
        print(f"\n  Core Area : {estimate.core_area_um2:.0f} µm²")
        print(f"    Width  : {estimate.core_width_um:.0f} µm")
        print(f"    Height : {estimate.core_height_um:.0f} µm")
        print(f"\n  Die Area  : {estimate.die_width_um * estimate.die_height_um:.0f} µm²")
        print(f"    Width  : {estimate.die_width_um:.0f} µm")
        print(f"    Height : {estimate.die_height_um:.0f} µm")
        print(f"\n  Util      : {estimate.actual_utilization*100:.1f}% (target {estimate.target_utilization*100:.0f}%)")
        print("="*70 + "\n")
