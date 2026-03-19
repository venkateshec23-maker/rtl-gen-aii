"""
Area Analyzer

Estimates chip area for RTL designs.

Usage:
    from python.area_analyzer import AreaAnalyzer
    
    analyzer = AreaAnalyzer()
    result = analyzer.analyze_area(rtl_code, synthesis_results)
"""

import re
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import json
from datetime import datetime


class AreaAnalyzer:
    """Chip area estimation and analysis."""
    
    def __init__(self, technology_nm: int = 45):
        """
        Initialize area analyzer.
        
        Args:
            technology_nm: Technology node in nanometers
        """
        self.technology_nm = technology_nm
        
        # Gate area models (in square microns, normalized to 2-input NAND)
        self.gate_areas = {
            'nand2': 1.0,
            'nor2': 1.2,
            'and2': 1.1,
            'or2': 1.3,
            'xor2': 2.5,
            'not': 0.6,
            'buf': 0.8,
            'mux2': 3.0,
            'flipflop': 6.0,
            'latch': 4.0,
            'adder_bit': 12.0,
            'multiplier_bit': 25.0,
            'sram_bit': 0.5,
        }
        
        # Technology scaling factor (area scales with square of feature size)
        self.tech_scale = (technology_nm / 45.0) ** 2
        
        # Apply scaling
        for gate, area in self.gate_areas.items():
            self.gate_areas[gate] *= self.tech_scale
    
    def analyze_area(
        self,
        rtl_code: str,
        module_name: str,
        synthesis_results: Optional[Dict] = None
    ) -> Dict:
        """
        Analyze area of design.
        
        Args:
            rtl_code: RTL code
            module_name: Module name
            synthesis_results: Optional synthesis results
            
        Returns:
            dict: Area analysis results
        """
        print(f"\n{'='*70}")
        print(f"AREA ANALYSIS: {module_name}")
        print(f"{'='*70}")
        
        # Analyze design structure
        design_info = self._analyze_design_structure(rtl_code)
        
        # Estimate area from RTL
        rtl_area = self._estimate_rtl_area(design_info)
        
        # If synthesis results available, use those
        if synthesis_results and 'gate_count' in synthesis_results:
            synth_area = self._estimate_synthesis_area(synthesis_results)
        else:
            synth_area = None
        
        results = {
            'module_name': module_name,
            'technology_nm': self.technology_nm,
            'design_info': design_info,
            'rtl_area_estimate': rtl_area,
            'synthesis_area_estimate': synth_area,
            'final_area': synth_area if synth_area else rtl_area,
        }
        
        # Print summary
        self._print_area_summary(results)
        
        return results
    
    def _analyze_design_structure(self, rtl_code: str) -> Dict:
        """Analyze RTL structure for area estimation."""
        info = {
            'registers': 0,
            'latches': 0,
            'combinational_gates': 0,
            'muxes': 0,
            'adders': 0,
            'subtractors': 0,
            'multipliers': 0,
            'comparators': 0,
            'bit_width': 8,
            'memory_bits': 0,
            'total_lines': len(rtl_code.split('\n')),
        }
        
        # Count registers
        info['registers'] = len(re.findall(r'\breg\s+(?:\[.*?\])?\s*\w+', rtl_code))
        
        # Count latches
        info['latches'] = len(re.findall(r'always @\(.*?\)', rtl_code)) - len(re.findall(r'always @\(posedge', rtl_code))
        
        # Estimate bit width
        width_matches = re.findall(r'\[(\d+):0\]', rtl_code)
        if width_matches:
            info['bit_width'] = max(int(w) for w in width_matches) + 1
        
        # Count operators
        info['combinational_gates'] = (
            rtl_code.count('&') + rtl_code.count('|') +
            rtl_code.count('^') + rtl_code.count('~')
        )
        
        # Count muxes
        info['muxes'] = rtl_code.count('?') + len(re.findall(r'case\s*\(', rtl_code)) * 2
        
        # Count arithmetic units
        info['adders'] = rtl_code.count('+')
        info['subtractors'] = rtl_code.count('-')
        info['multipliers'] = rtl_code.count('*')
        info['comparators'] = rtl_code.count('>') + rtl_code.count('<') + rtl_code.count('==')
        
        # Estimate memory
        mem_matches = re.findall(r'reg\s+\[(\d+):0\]\s+\w+\s*\[(\d+):0\]', rtl_code)
        for width_str, depth_str in mem_matches:
            width = int(width_str) + 1
            depth = int(depth_str) + 1
            info['memory_bits'] += width * depth
        
        return info
    
    def _estimate_rtl_area(self, design_info: Dict) -> Dict:
        """Estimate area from RTL analysis."""
        area_um2 = 0.0
        breakdown = {}
        
        # Register area
        register_area = design_info['registers'] * self.gate_areas['flipflop']
        breakdown['registers'] = register_area
        area_um2 += register_area
        
        # Latch area
        latch_area = design_info['latches'] * self.gate_areas['latch']
        breakdown['latches'] = latch_area
        area_um2 += latch_area
        
        # Combinational logic area
        # Rough estimate: each operator is a 2-input gate
        logic_area = design_info['combinational_gates'] * self.gate_areas['and2']
        breakdown['combinational_logic'] = logic_area
        area_um2 += logic_area
        
        # Mux area
        mux_area = design_info['muxes'] * self.gate_areas['mux2']
        breakdown['muxes'] = mux_area
        area_um2 += mux_area
        
        # Adder area
        adder_area = design_info['adders'] * design_info['bit_width'] * self.gate_areas['adder_bit']
        breakdown['adders'] = adder_area
        area_um2 += adder_area
        
        # Subtractor area (similar to adder)
        sub_area = design_info['subtractors'] * design_info['bit_width'] * self.gate_areas['adder_bit']
        breakdown['subtractors'] = sub_area
        area_um2 += sub_area
        
        # Multiplier area
        mult_area = design_info['multipliers'] * (design_info['bit_width'] ** 2) * self.gate_areas['multiplier_bit']
        breakdown['multipliers'] = mult_area
        area_um2 += mult_area
        
        # Comparator area (simplified)
        comp_area = design_info['comparators'] * design_info['bit_width'] * self.gate_areas['xor2']
        breakdown['comparators'] = comp_area
        area_um2 += comp_area
        
        # Memory area
        memory_area = design_info['memory_bits'] * self.gate_areas['sram_bit']
        breakdown['memory'] = memory_area
        area_um2 += memory_area
        
        # Routing overhead (typical 40-60% of total)
        routing_overhead = area_um2 * 0.5
        breakdown['routing_overhead'] = routing_overhead
        area_um2 += routing_overhead
        
        return {
            'total_area_um2': area_um2,
            'total_area_mm2': area_um2 / 1_000_000,
            'breakdown': breakdown,
            'method': 'rtl_estimation',
        }
    
    def _estimate_synthesis_area(self, synthesis_results: Dict) -> Dict:
        """Estimate area from synthesis results."""
        gate_count = synthesis_results['gate_count']
        
        # Average area per gate (simplified)
        avg_gate_area = sum(self.gate_areas.values()) / len(self.gate_areas)
        
        # Total area with routing overhead
        logic_area = gate_count * avg_gate_area
        routing_overhead = logic_area * 0.5
        total_area = logic_area + routing_overhead
        
        breakdown = {
            'logic': logic_area,
            'routing_overhead': routing_overhead,
        }
        
        # Add cell type breakdown if available
        if 'cell_types' in synthesis_results:
            breakdown['cell_types'] = synthesis_results['cell_types']
        
        return {
            'total_area_um2': total_area,
            'total_area_mm2': total_area / 1_000_000,
            'gate_count': gate_count,
            'breakdown': breakdown,
            'method': 'synthesis_based',
        }
    
    def _print_area_summary(self, results: Dict):
        """Print area summary."""
        final_area = results['final_area']
        design_info = results['design_info']
        
        print(f"\nTechnology: {self.technology_nm}nm")
        print(f"\nDesign Statistics:")
        print(f"  Registers: {design_info['registers']}")
        print(f"  Combinational gates: {design_info['combinational_gates']}")
        print(f"  Arithmetic units: {design_info['adders']} adders, {design_info['multipliers']} multipliers")
        print(f"  Memory: {design_info['memory_bits']} bits")
        
        print(f"\nArea Estimate:")
        print(f"  Method: {final_area['method']}")
        print(f"  Total area: {final_area['total_area_um2']:.2f} µm²")
        print(f"  Total area: {final_area['total_area_mm2']:.6f} mm²")
        
        if 'gate_count' in final_area:
            print(f"  Gate count: {final_area['gate_count']}")
        
        print(f"\nArea Breakdown:")
        for component, area in sorted(final_area['breakdown'].items(), key=lambda x: x[1], reverse=True):
            if isinstance(area, (int, float)):
                pct = area / final_area['total_area_um2'] * 100
                print(f"  {component:20s}: {area:8.2f} µm² ({pct:5.1f}%)")
    
    def estimate_die_area(
        self,
        core_area_mm2: float,
        io_pads: int = 100,
        pad_pitch_um: float = 60.0
    ) -> Dict:
        """
        Estimate total die area including IO ring.
        
        Args:
            core_area_mm2: Core logic area
            io_pads: Number of IO pads
            pad_pitch_um: IO pad pitch in microns
            
        Returns:
            dict: Die area estimate
        """
        # Calculate die side based on core area (assume square)
        core_side_mm = (core_area_mm2 ** 0.5)
        
        # IO ring width (2 rows of pads)
        io_ring_width_um = pad_pitch_um * 2
        io_ring_width_mm = io_ring_width_um / 1000
        
        # Die side with IO ring
        die_side_mm = core_side_mm + 2 * io_ring_width_mm
        
        # Die area
        die_area_mm2 = die_side_mm ** 2
        
        # IO area
        io_area_mm2 = die_area_mm2 - core_area_mm2
        
        return {
            'core_area_mm2': core_area_mm2,
            'io_area_mm2': io_area_mm2,
            'total_die_area_mm2': die_area_mm2,
            'die_side_mm': die_side_mm,
            'io_pads': io_pads,
            'pad_pitch_um': pad_pitch_um,
        }
    
    def compare_implementations(
        self,
        implementations: List[Tuple[str, str]]
    ) -> Dict:
        """
        Compare area of different implementations.
        
        Args:
            implementations: List of (name, rtl_code) tuples
            
        Returns:
            dict: Comparison results
        """
        print(f"\n{'='*70}")
        print("IMPLEMENTATION AREA COMPARISON")
        print(f"{'='*70}")
        
        results = []
        
        for name, rtl_code in implementations:
            print(f"\nAnalyzing: {name}")
            result = self.analyze_area(rtl_code, name)
            results.append({
                'name': name,
                'area': result,
            })
        
        # Print comparison
        print(f"\n{'='*70}")
        print("COMPARISON")
        print(f"{'='*70}")
        
        print(f"\n{'Implementation':<25} {'Area (µm²)':<15} {'Area (mm²)':<15} {'Relative':<10}")
        print("-" * 70)
        
        min_area = min(r['area']['final_area']['total_area_um2'] for r in results)
        
        for result in results:
            area_um2 = result['area']['final_area']['total_area_um2']
            area_mm2 = result['area']['final_area']['total_area_mm2']
            relative = area_um2 / min_area
            
            print(f"{result['name']:<25} {area_um2:<15.2f} {area_mm2:<15.6f} {relative:<10.2f}x")
        
        return {
            'implementations': results,
            'smallest': min(results, key=lambda x: x['area']['final_area']['total_area_um2']),
            'largest': max(results, key=lambda x: x['area']['final_area']['total_area_um2']),
        }


# ============================================================================
# SELF-TEST
# ============================================================================

if __name__ == "__main__":
    print("Area Analyzer Self-Test\n")
    
    analyzer = AreaAnalyzer(technology_nm=45)
    
    # Test design
    rtl_code = """
module alu_16bit(
    input [15:0] a,
    input [15:0] b,
    input [2:0] op,
    output reg [15:0] result
);
    always @(*) begin
        case (op)
            3'b000: result = a + b;
            3'b001: result = a - b;
            3'b010: result = a & b;
            3'b011: result = a | b;
            3'b100: result = a ^ b;
            3'b101: result = a * b;
            default: result = 16'b0;
        endcase
    end
endmodule
"""
    
    # Analyze area
    result = analyzer.analyze_area(rtl_code, 'alu_16bit')
    
    # Estimate die area
    die_area = analyzer.estimate_die_area(
        core_area_mm2=result['final_area']['total_area_mm2'],
        io_pads=50
    )
    
    print(f"\nDie Area Estimate:")
    print(f"  Core: {die_area['core_area_mm2']:.6f} mm²")
    print(f"  IO: {die_area['io_area_mm2']:.6f} mm²")
    print(f"  Total: {die_area['total_die_area_mm2']:.6f} mm²")
    print(f"  Die side: {die_area['die_side_mm']:.3f} mm")
    
    print("\n✓ Self-test complete")
