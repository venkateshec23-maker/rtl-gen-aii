"""
Synthesis Engine

Integrates with Yosys and other synthesis tools for logic synthesis.

Usage:
    from python.synthesis_engine import SynthesisEngine

    engine = SynthesisEngine()
    result = engine.synthesize(rtl_code, module_name)
"""

import subprocess
from pathlib import Path
from typing import Dict, List, Optional
import re
import json
from datetime import datetime


class SynthesisEngine:
    """Logic synthesis engine using Yosys."""

    def __init__(self, work_dir: str = 'synthesis_work'):
        """
        Initialize synthesis engine.

        Args:
            work_dir: Working directory for synthesis files
        """
        self.work_dir = Path(work_dir)
        self.work_dir.mkdir(exist_ok=True)

        # Check if Yosys is available
        self.yosys_available = self._check_yosys()

        # Default synthesis options
        self.synthesis_options = {
            'optimization_level': 2,
            'target_technology': 'generic',
            'abc_script': '+strash;scorr;dc2;dretime;strash;dch,-f;map,-M,1',
        }

    def _check_yosys(self) -> bool:
        """Check if Yosys is available."""
        try:
            result = subprocess.run(
                ['yosys', '-V'],
                capture_output=True,
                text=True,
                timeout=5
            )
            return result.returncode == 0
        except:
            return False

    def create_synthesis_script(
        self,
        rtl_file: str,
        module_name: str,
        output_file: str
    ) -> str:
        """
        Create Yosys synthesis script.

        Args:
            rtl_file: Input RTL file
            module_name: Top module name
            output_file: Output netlist file

        Returns:
            str: Script content
        """
        script = f"""# Yosys synthesis script
# Generated: {datetime.now().isoformat()}

# Read design
read_verilog {rtl_file}

# Elaborate design
hierarchy -check -top {module_name}

# Synthesis
proc
opt
fsm
opt
memory
opt

# Technology mapping
techmap
opt

# ABC optimization (if available)
catch {{abc -lut 4}}

# Clean up
clean

# Statistics
stat

# Write output
write_verilog {output_file}
"""
        return script

    def synthesize(
        self,
        rtl_code: str,
        module_name: str,
        technology: str = 'generic'
    ) -> Dict:
        """
        Synthesize RTL code.

        Args:
            rtl_code: RTL code to synthesize
            module_name: Module name
            technology: Target technology

        Returns:
            dict: Synthesis results
        """
        print(f"\n{'='*70}")
        print(f"SYNTHESIS: {module_name}")
        print(f"{'='*70}")

        if not self.yosys_available:
            print(f"\n[INFO] Yosys not available - using Python-based fallback analyzer")
            print(f"       For full synthesis: apt-get install yosys (Linux) or choco install yosys (Windows)")
            return self._fallback_synthesis(rtl_code, module_name)

        # Create work directory for this synthesis
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        work_subdir = self.work_dir / f"{module_name}_{timestamp}"
        work_subdir.mkdir(exist_ok=True)

        # Write RTL to file
        rtl_file = work_subdir / f"{module_name}.v"
        rtl_file.write_text(rtl_code)

        # Output files
        netlist_file = work_subdir / f"{module_name}_synth.v"
        script_file = work_subdir / 'synthesis.ys'
        log_file = work_subdir / 'synthesis.log'

        # Create synthesis script
        script = self.create_synthesis_script(
            rtl_file=str(rtl_file),
            module_name=module_name,
            output_file=str(netlist_file)
        )
        script_file.write_text(script)

        print(f"\nRunning synthesis...")
        print(f"  RTL file: {rtl_file}")
        print(f"  Script: {script_file}")

        try:
            # Run Yosys
            result = subprocess.run(
                ['yosys', '-s', str(script_file)],
                capture_output=True,
                text=True,
                timeout=60,
                cwd=str(work_subdir)
            )

            # Save log
            log_file.write_text(result.stdout + '\n' + result.stderr)

            if result.returncode != 0:
                return {
                    'success': False,
                    'message': 'Synthesis failed',
                    'log': result.stderr,
                    'log_file': str(log_file),
                }

            print(f"  [PASS] Synthesis complete")

            # Parse results
            results = self._parse_synthesis_results(result.stdout, work_subdir)

            results.update({
                'success': True,
                'netlist_file': str(netlist_file),
                'log_file': str(log_file),
                'work_dir': str(work_subdir),
            })

            # Print summary
            self._print_synthesis_summary(results)

            return results

        except subprocess.TimeoutExpired:
            return {
                'success': False,
                'message': 'Synthesis timeout (>60s)',
            }
        except Exception as e:
            return {
                'success': False,
                'message': f'Synthesis error: {str(e)}',
            }

    def _fallback_synthesis(self, rtl_code: str, module_name: str) -> Dict:
        """
        Fallback Python-based synthesis analyzer (when Yosys unavailable).
        
        Provides gate count estimation and basic cell analysis without
        external tools.
        """
        print(f"\n[FALLBACK] Analyzing RTL structure for gate count estimation...")
        
        # Analyze RTL structure
        design_info = self._analyze_rtl_structure(rtl_code)
        
        # Estimate gate count
        gate_count = self._estimate_gate_count(design_info)
        
        # Build cell library for this design
        cell_types = self._estimate_cell_types(design_info, gate_count)
        
        results = {
            'success': True,
            'method': 'fallback_python_analyzer',
            'gate_count': gate_count,
            'cell_types': cell_types,
            'design_info': design_info,
            'warnings': [
                'Using Python fallback analyzer (Yosys not available)',
                'Gate count is estimated, not actual synthesis result',
                'For accurate results, install Yosys',
            ],
        }
        
        self._print_synthesis_summary(results)
        return results
    
    def _analyze_rtl_structure(self, rtl_code: str) -> Dict:
        """Analyze RTL structure for gate estimation."""
        info = {
            'registers': len(re.findall(r'\breg\s+', rtl_code)),
            'wires': len(re.findall(r'\bwire\s+', rtl_code)),
            'logic_ops': rtl_code.count('&') + rtl_code.count('|') + rtl_code.count('^'),
            'arithmetic_ops': rtl_code.count('+') + rtl_code.count('-'),
            'multipliers': rtl_code.count('*'),
            'comparators': rtl_code.count('==') + rtl_code.count('!=') + rtl_code.count('<') + rtl_code.count('>'),
            'muxes': rtl_code.count('?') + len(re.findall(r'case\s*\(', rtl_code)) * 2,
            'bit_width': self._extract_max_bit_width(rtl_code),
        }
        return info
    
    def _extract_max_bit_width(self, rtl_code: str) -> int:
        """Extract maximum bit width from RTL."""
        width_matches = re.findall(r'\[(\d+):0\]', rtl_code)
        if width_matches:
            return max(int(w) for w in width_matches) + 1
        return 8  # Default
    
    def _estimate_gate_count(self, design_info: Dict) -> int:
        """Estimate total gate count from design structure."""
        count = 0
        
        # Register gates (flipflop = ~6-8 gates)
        count += design_info['registers'] * 6
        
        # Logic operation gates (2-input gate = 1 gate, but typically needs multiple)
        count += design_info['logic_ops'] * 1
        
        # Arithmetic gates (adder bit = ~20 gates, multiplier bit = ~50 gates)
        count += design_info['arithmetic_ops'] * design_info['bit_width'] * 5
        count += design_info['multipliers'] * (design_info['bit_width'] ** 2) * 2
        
        # Comparator gates
        count += design_info['comparators'] * design_info['bit_width'] * 2
        
        # Mux gates (2:1 mux = ~3-4 gates)
        count += design_info['muxes'] * 3
        
        # Add control logic overhead (~20% of total)
        count = int(count * 1.2)
        
        # Minimum gate count
        return max(count, 10)
    
    def _estimate_cell_types(self, design_info: Dict, gate_count: int) -> Dict:
        """Estimate distribution of cell types."""
        cells = {}
        
        # Proportional distribution based on operations
        total_ops = (
            design_info['logic_ops'] + 
            design_info['arithmetic_ops'] +
            design_info['multipliers'] +
            design_info['comparators'] +
            design_info['muxes']
        )
        
        if total_ops > 0:
            factor = gate_count / total_ops
            
            cells['AND2'] = int(design_info['logic_ops'] * 0.3 * factor)
            cells['OR2'] = int(design_info['logic_ops'] * 0.3 * factor)
            cells['XOR2'] = int(design_info['logic_ops'] * 0.4 * factor)
            cells['ADDER_1B'] = int(design_info['arithmetic_ops'] * design_info['bit_width'] * factor)
            cells['MUX2'] = int(design_info['muxes'] * factor)
            cells['DFF'] = int(design_info['registers'] * factor)
        
        # Remove zero entries
        cells = {k: v for k, v in cells.items() if v > 0}
        
        return cells

    def _parse_synthesis_results(self, log: str, work_dir: Path) -> Dict:
        """Parse synthesis results from log."""
        results = {
            'gate_count': 0,
            'cell_types': {},
            'warnings': [],
            'errors': [],
        }

        # Parse statistics
        cell_match = re.search(r'Number of cells:\s+(\d+)', log)
        if cell_match:
            results['gate_count'] = int(cell_match.group(1))

        # Parse warnings and errors
        for line in log.split('\n'):
            if 'Warning' in line:
                results['warnings'].append(line.strip())
            elif 'ERROR' in line:
                results['errors'].append(line.strip())

        return results

    def _print_synthesis_summary(self, results: Dict):
        """Print synthesis summary."""
        print(f"\nSynthesis Results:")
        print(f"  Total gates: {results.get('gate_count', 0)}")

        cell_types = results.get('cell_types', {})
        if cell_types:
            print(f"\n  Cell types:")
            for cell_type, count in sorted(cell_types.items(), key=lambda x: x[1], reverse=True):
                print(f"    {cell_type}: {count}")

        warnings = results.get('warnings', [])
        if warnings:
            print(f"\n  Warnings: {len(warnings)}")
            for warning in warnings[:3]:
                print(f"    - {warning[:80]}...")

        errors = results.get('errors', [])
        if errors:
            print(f"\n  Errors: {len(errors)}")

    def estimate_area(self, gate_count: int, technology: str = 'generic') -> Dict:
        """
        Estimate chip area from gate count.

        Args:
            gate_count: Number of gates
            technology: Target technology

        Returns:
            dict: Area estimates
        """
        if technology == 'generic':
            area_um2 = gate_count * 1.0
        elif technology == 'fpga':
            luts = gate_count // 2
            return {
                'luts': luts,
                'technology': technology,
            }
        else:
            area_um2 = gate_count * 1.0

        return {
            'area_um2': area_um2,
            'area_mm2': area_um2 / 1_000_000,
            'gate_count': gate_count,
            'technology': technology,
        }

    def estimate_power(self, gate_count: int, frequency_mhz: float = 100) -> Dict:
        """
        Estimate power consumption.

        Args:
            gate_count: Number of gates
            frequency_mhz: Operating frequency in MHz

        Returns:
            dict: Power estimates
        """
        # Rough power estimation
        dynamic_power_nw = gate_count * frequency_mhz * 0.1
        leakage_power_nw = gate_count * 1.0
        total_power_nw = dynamic_power_nw + leakage_power_nw

        return {
            'dynamic_power_mw': dynamic_power_nw / 1_000_000,
            'leakage_power_mw': leakage_power_nw / 1_000_000,
            'total_power_mw': total_power_nw / 1_000_000,
            'frequency_mhz': frequency_mhz,
            'note': 'Rough estimate - actual power depends on technology and activity',
        }


if __name__ == "__main__":
    print("Synthesis Engine Self-Test\n")

    engine = SynthesisEngine()

    if not engine.yosys_available:
        print("⚠ Yosys not available")
        print("Install with: apt-get install yosys")
        print("\nContinuing with limited testing...\n")

    # Test with simple design
    rtl_code = """
module adder_4bit(
    input [3:0] a,
    input [3:0] b,
    output [3:0] sum,
    output cout
);
    assign {cout, sum} = a + b;
endmodule
"""

    result = engine.synthesize(rtl_code, 'adder_4bit')

    if result['success']:
        print("\n[PASS] Synthesis successful")

        # Test area estimation
        area = engine.estimate_area(result['gate_count'])
        print(f"\nArea estimate:")
        print(f"  Area: {area['area_um2']:.2f} µm²")
        print(f"  Area: {area['area_mm2']:.6f} mm²")

        # Test power estimation
        power = engine.estimate_power(result['gate_count'], frequency_mhz=100)
        print(f"\nPower estimate @ 100 MHz:")
        print(f"  Dynamic: {power['dynamic_power_mw']:.4f} mW")
        print(f"  Leakage: {power['leakage_power_mw']:.4f} mW")
        print(f"  Total: {power['total_power_mw']:.4f} mW")
    else:
        print(f"\n[FAIL] Synthesis failed: {result.get('message', 'Unknown error')}")

    print("\n[PASS] Self-test complete")
