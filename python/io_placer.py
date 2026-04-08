"""
io_placer.py  –  I/O Pin Placement Generator (Sky130)
=====================================================
Parses Verilog port declarations, classifies pin types (clock, data, power),
and assigns them to die edges with exact µm coordinates.

Usage:
    from python.io_placer import IOPlacer
    placer = IOPlacer(core_width=1000, core_height=800)
    pins = placer.assign_pins_from_verilog("design.v")
    tcl_script= placer.generate_place_pin_tcl(pins)

Output: Tcl script with `place_pin` commands for OpenROAD
"""

from __future__ import annotations

import re
import logging
from dataclasses import dataclass
from enum import Enum
from typing import Dict, List, Optional, Tuple


# ──────────────────────────────────────────────────────────────────────────────
# ENUMERATIONS
# ──────────────────────────────────────────────────────────────────────────────

class PinType(Enum):
    """Logical pin classification."""
    CLOCK = "clock"
    RESET = "reset"
    ENABLE = "enable"
    DATA_IN = "data_in"
    DATA_OUT = "data_out"
    POWER = "power"
    GROUND = "ground"


class DieEdge(Enum):
    """Die edge location."""
    TOP = "top"
    BOTTOM = "bottom"
    LEFT = "left"
    RIGHT = "right"


# ──────────────────────────────────────────────────────────────────────────────
# DATA CLASSES
# ──────────────────────────────────────────────────────────────────────────────

@dataclass
class IOPin:
    """I/O pin with location and attributes."""
    name: str
    pin_type: PinType
    direction: str  # "input", "output", "inout"
    width: int = 1  # Bit width
    
    # Placement
    edge: DieEdge = DieEdge.LEFT
    x_um: float = 0.0
    y_um: float = 0.0
    layer: str = "met4"  # Placement layer


# ──────────────────────────────────────────────────────────────────────────────
# I/O PLACER
# ──────────────────────────────────────────────────────────────────────────────

class IOPlacer:
    """Places I/O pins around die perimeter."""
    
    def __init__(
        self,
        core_width: float,
        core_height: float,
        pin_pitch_um: float = 50.0
    ):
        self.logger = logging.getLogger(__name__)
        self.core_width = core_width
        self.core_height = core_height
        self.pin_pitch_um = pin_pitch_um
        self.margin_um = 20.0  # Distance from corner
        
        # Port name patterns
        self.clock_patterns = [r"clk", r"clock", r"clk_.*"]
        self.reset_patterns = [r"rst", r"reset", r"rst_.*"]
        self.enable_patterns = [r"en", r"enable", r".*_en"]
    
    def assign_pins_from_verilog(self, verilog_file: str) -> List[IOPin]:
        """
        Parse Verilog module interfaces and assign pin locations.
        
        Args:
            verilog_file: Path to Verilog module
        
        Returns: List of IOPin with assignments
        """
        pins = []
        
        try:
            with open(verilog_file, "r") as f:
                content = f.read()
            
            # Find module declaration - handle both Verilog-2001 (ports in header) and Verilog-1995 (separate declarations)
            module_match = re.search(r"module\s+(\w+)\s*\((.*?)\)", content, re.DOTALL)
            if not module_match:
                self.logger.warning("No module found in Verilog")
                return pins
            
            # For Verilog-1995 format, search entire file for input/output declarations
            # Pattern: input|output [width] port_name
            port_patterns = [
                (r"input\s+(?:\[.*?\])?\s*(\w+)", "input"),
                (r"output\s+(?:\[.*?\])?\s*(\w+)", "output"),
                (r"inout\s+(?:\[.*?\])?\s*(\w+)", "inout"),
            ]
            
            for pattern, direction in port_patterns:
                matches = re.findall(pattern, content)
                for port_name in matches:
                    pin_type = self._classify_pin(port_name)
                    pin = IOPin(
                        name=port_name,
                        pin_type=pin_type,
                        direction=direction,
                        width=1
                    )
                    pins.append(pin)
            
            # Assign locations
            if pins:
                self._assign_locations(pins)
            else:
                self.logger.warning(f"No input/output ports found in {verilog_file}")
        
        except Exception as e:
            self.logger.error(f"Failed to parse Verilog: {e}")
        
        return pins
    
    def _classify_pin(self, port_name: str) -> PinType:
        """Classify pin by name patterns."""
        port_lower = port_name.lower()
        
        # Check patterns
        for pattern in self.clock_patterns:
            if re.search(pattern, port_lower):
                return PinType.CLOCK
        
        for pattern in self.reset_patterns:
            if re.search(pattern, port_lower):
                return PinType.RESET
        
        for pattern in self.enable_patterns:
            if re.search(pattern, port_lower):
                return PinType.ENABLE
        
        # Check VDD/VSS
        if port_name in ["VDD", "VCCD", "VCC"] or "power" in port_lower:
            return PinType.POWER
        
        if port_name in ["VSS", "GND", "GNDD"] or "gnd" in port_lower or "ground" in port_lower:
            return PinType.GROUND
        
        # Default by direction
        if "in" in port_lower:
            return PinType.DATA_IN
        else:
            return PinType.DATA_OUT
    
    def _assign_locations(self, pins: List[IOPin]):
        """Assign µm coordinates based on pin type and position."""
        
        # Group pins by edge
        clocks = [p for p in pins if p.pin_type == PinType.CLOCK]
        resets = [p for p in pins if p.pin_type == PinType.RESET]
        inputs = [p for p in pins if p.pin_type == PinType.DATA_IN]
        outputs = [p for p in pins if p.pin_type == PinType.DATA_OUT]
        power_pins = [p for p in pins if p.pin_type == PinType.POWER]
        ground_pins = [p for p in pins if p.pin_type == PinType.GROUND]
        
        # Assign edges
        # Clocks → top
        self._place_on_edge(clocks, DieEdge.TOP)
        # Resets → top right
        self._place_on_edge(resets, DieEdge.TOP)
        # Inputs → left
        self._place_on_edge(inputs, DieEdge.LEFT)
        # Outputs → right
        self._place_on_edge(outputs, DieEdge.RIGHT)
        # Power → top/bottom
        self._place_on_edge(power_pins + ground_pins, DieEdge.BOTTOM)
    
    def _place_on_edge(self, pins: List[IOPin], edge: DieEdge):
        """Place pins along a specific edge."""
        if not pins:
            return
        
        num_pins = len(pins)
        
        if edge == DieEdge.TOP:
            y = self.core_height + self.margin_um
            x_start = self.margin_um
            x_end = self.core_width - self.margin_um
            spacing = (x_end - x_start) / max(num_pins - 1, 1)
            for i, pin in enumerate(pins):
                pin.edge = DieEdge.TOP
                pin.x_um = x_start + i * spacing
                pin.y_um = y
        
        elif edge == DieEdge.BOTTOM:
            y = -self.margin_um
            x_start = self.margin_um
            x_end = self.core_width - self.margin_um
            spacing = (x_end - x_start) / max(num_pins - 1, 1)
            for i, pin in enumerate(pins):
                pin.edge = DieEdge.BOTTOM
                pin.x_um = x_start + i * spacing
                pin.y_um = y
        
        elif edge == DieEdge.LEFT:
            x = -self.margin_um
            y_start = self.margin_um
            y_end = self.core_height - self.margin_um
            spacing = (y_end - y_start) / max(num_pins - 1, 1)
            for i, pin in enumerate(pins):
                pin.edge = DieEdge.LEFT
                pin.x_um = x
                pin.y_um = y_start + i * spacing
        
        elif edge == DieEdge.RIGHT:
            x = self.core_width + self.margin_um
            y_start = self.margin_um
            y_end = self.core_height - self.margin_um
            spacing = (y_end - y_start) / max(num_pins - 1, 1)
            for i, pin in enumerate(pins):
                pin.edge = DieEdge.RIGHT
                pin.x_um = x
                pin.y_um = y_start + i * spacing
    
    def generate_place_pin_tcl(self, pins: List[IOPin]) -> str:
        """Generate OpenROAD Tcl commands for pin placement."""
        tcl_lines = [
            "# I/O Pin Placement",
            ""
        ]
        
        for pin in pins:
            # place_pin {pin_name} -side {side} -location {x} {y}
            side = pin.edge.value.upper()
            tcl_lines.append(
                f'place_pin {pin.name} -side {side} -location {pin.x_um:.1f} {pin.y_um:.1f}'
            )
        
        tcl_lines.append("")
        return "\n".join(tcl_lines)
    
    def print_pins(self, pins: List[IOPin]):
        """Print formatted pin assignments."""
        print("\n" + "="*70)
        print("  I/O Pin Placement  –  RTL-Gen AI")
        print("="*70)
        
        for edge in DieEdge:
            edge_pins = [p for p in pins if p.edge == edge]
            if edge_pins:
                print(f"\n  {edge.value.upper()}:")
                for pin in edge_pins:
                    print(f"    {pin.name:20s} ({pin.pin_type.value:10s}) @ ({pin.x_um:7.1f}, {pin.y_um:7.1f})")
        
        print("\n" + "="*70 + "\n")
