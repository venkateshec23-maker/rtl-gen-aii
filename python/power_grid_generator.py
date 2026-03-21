"""
power_grid_generator.py  –  Power Distribution Network (PDN) Generator
======================================================================
Generates complete OpenROAD pdngen configuration for multi-layer power grids.
Includes:
  - Core VDD/VSS rails (metal1)
  - Vertical stripes (metal4)
  - Horizontal stripes (metal5)
  - Core ring + via connections

Usage:
    from python.power_grid_generator import PowerGridGenerator
    gen = PowerGridGenerator(core_width=1000, core_height=800)
    tcl_script = gen.generate_pdngen_config(
        power_pin="VDD",
        ground_pin="VSS"
    )

Output: OpenROAD pdngen Tcl configuration
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from enum import Enum
from typing import Optional


# ──────────────────────────────────────────────────────────────────────────────
# ENUMERATIONS
# ──────────────────────────────────────────────────────────────────────────────

class StripeType(Enum):
    """Power stripe configuration."""
    VERTICAL = "vertical"
    HORIZONTAL = "horizontal"


# ──────────────────────────────────────────────────────────────────────────────
# DATA CLASSES
# ──────────────────────────────────────────────────────────────────────────────

@dataclass
class PowerStripConfig:
    """Configuration for power stripe."""
    layer: str              # metal2, metal4, etc
    pitch_um: float         # Distance between stripes
    width_um: float         # Width of stripe
    spacing_um: float       # Space to keep from edge


# ──────────────────────────────────────────────────────────────────────────────
# POWER GRID GENERATOR
# ──────────────────────────────────────────────────────────────────────────────

class PowerGridGenerator:
    """Generates multi-layer power distribution network."""
    
    def __init__(
        self,
        core_width: float,
        core_height: float,
        power_pin: str = "VDD",
        ground_pin: str = "VSS"
    ):
        self.logger = logging.getLogger(__name__)
        self.core_width = core_width
        self.core_height = core_height
        self.power_pin = power_pin
        self.ground_pin = ground_pin
        
        # Default stripe configuration
        self.rail_width_um = 1.0      # M1 rail width
        self.rail_pitch_um = 10.0     # M1 rail pitch
        self.stripe_width_um = 4.0
        self.stripe_pitch_um = 100.0
    
    def generate_pdngen_config(self) -> str:
        """
        Generate complete pdngen configuration script.
        
        Returns: Tcl script for OpenROAD pdngen command
        """
        
        tcl_lines = [
            "# Power Grid Generation",
            "# ========================",
            ""
        ]
        
        # Define layers
        tcl_lines.extend(self._layer_definitions())
        
        # Core ring
        tcl_lines.extend(self._core_ring_config())
        
        # Metal1 rails
        tcl_lines.extend(self._metal1_rails())
        
        # Metal4 vertical stripes
        tcl_lines.extend(self._metal4_stripes())
        
        # Metal5 horizontal stripes
        tcl_lines.extend(self._metal5_stripes())
        
        # Via connections
        tcl_lines.extend(self._via_connections())
        
        # Run pdngen
        tcl_lines.extend([
            "",
            "# Run power grid generation",
            "pdngen",
            ""
        ])
        
        return "\n".join(tcl_lines)
    
    def _layer_definitions(self) -> list:
        """Define power/ground layers."""
        lines = [
            "# Layer definitions",
            "set_layer VDD {",
            f"  layer metal1",
            f"  layer metal4",
            f"  layer metal5",
            "}",
            "",
            "set_layer VSS {",
            f"  layer metal1",
            f"  layer metal4",
            f"  layer metal5",
            "}",
            ""
        ]
        return lines
    
    def _core_ring_config(self) -> list:
        """Define core power ring."""
        ring_width = 4.0
        ring_margin = 2.0
        
        x1 = ring_margin
        y1 = ring_margin
        x2 = self.core_width - ring_margin
        y2 = self.core_height - ring_margin
        
        lines = [
            "# Core power ring",
            "add_ring {",
            f"  name   power_ring",
            f"  layer  {{metal5 metal4 metal4 metal4}}",
            f"  width  {ring_width}",
            f"  spacing 0 0",
            f"  core {x1} {y1} {x2} {y2}",
            f"  vdd {self.power_pin}",
            f"  gnd {self.ground_pin}",
            "}",
            ""
        ]
        return lines
    
    def _metal1_rails(self) -> list:
        """Define metal1 VDD/VSS rails in each cell row."""
        lines = [
            "# Metal1 cell rail configuration",
            "add_rails {",
            f"  layer metal1",
            f"  vdd {{name {self.power_pin}}}",
            f"  gnd {{name {self.ground_pin}}}",
            f"  spacing {self.rail_pitch_um}",
            f"  width {self.rail_width_um}",
            "}",
            ""
        ]
        return lines
    
    def _metal4_stripes(self) -> list:
        """Define metal4 vertical stripes."""
        lines = [
            "# Metal4 vertical stripes",
            "add_straps {",
            f"  layer metal4",
            f"  direction vertical",
            f"  spacing {self.stripe_pitch_um}",
            f"  width {self.stripe_width_um}",
            f"  offset 10",
            f"  vdd {self.power_pin}",
            f"  gnd {self.ground_pin}",
            "}",
            ""
        ]
        return lines
    
    def _metal5_stripes(self) -> list:
        """Define metal5 horizontal stripes."""
        lines = [
            "# Metal5 horizontal stripes",
            "add_straps {",
            f"  layer metal5",
            f"  direction horizontal",
            f"  spacing {self.stripe_pitch_um}",
            f"  width {self.stripe_width_um}",
            f"  offset 10",
            f"  vdd {self.power_pin}",
            f"  gnd {self.ground_pin}",
            "}",
            ""
        ]
        return lines
    
    def _via_connections(self) -> list:
        """Define via connectivity between layers."""
        lines = [
            "# Via connectivity",
            "connect {",
            f"  metal1 metal4 via1",
            f"  metal4 metal5 via4",
            "}",
            ""
        ]
        return lines
    
    def generate_pdn_halo(self) -> str:
        """Generate halo (margin) configuration safe zone."""
        halo_um = 2.0
        
        tcl = f"""
# Halo configuration (keep-out zone around power grid)
set_power_halo {{
    left   {halo_um}
    right  {halo_um}
    top    {halo_um}
    bottom {halo_um}
}}
"""
        return tcl.strip()
    
    def print_config(self):
        """Print configuration summary."""
        print("\n" + "="*70)
        print("  Power Grid Configuration  –  RTL-Gen AI")
        print("="*70)
        print(f"  Core Size     : {self.core_width:.0f} x {self.core_height:.0f} µm")
        print(f"\n  Rail Config   :")
        print(f"    Width      : {self.rail_width_um} µm")
        print(f"    Pitch      : {self.rail_pitch_um} µm")
        print(f"\n  Stripe Config :")
        print(f"    Width      : {self.stripe_width_um} µm")
        print(f"    Pitch      : {self.stripe_pitch_um} µm")
        print(f"\n  Power Pins    : {self.power_pin} (VDD), {self.ground_pin} (VSS)")
        print(f"\n  Layers        : Metal1 (rails), Metal4/5 (stripes)")
        print("="*70 + "\n")
