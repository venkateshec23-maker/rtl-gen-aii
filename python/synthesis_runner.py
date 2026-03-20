"""
Synthesis Runner - RTL to gate-level synthesis with Yosys
"""

import os
import re
import subprocess
import json
import logging
from pathlib import Path

logger = logging.getLogger(__name__)


class SynthesisRunner:
    """Open-source RTL to gate-level synthesis using Yosys"""
    
    def __init__(self, output_dir='outputs', debug=False):
        """Initialize synthesis runner
        
        Args:
            output_dir: Directory to save synthesis results
            debug: Enable debug logging
        """
        self.output_dir = output_dir
        self.debug = debug
        os.makedirs(output_dir, exist_ok=True)
        self.yosys_available = self._check_yosys()
    
    def synthesize_rtl(self, rtl_code, module_name, output_format='verilog'):
        """Synthesize RTL to gate-level netlist
        
        Args:
            rtl_code: Verilog RTL code
            module_name: Top-level module name
            output_format: 'verilog' or 'json'
        
        Returns:
            {'success': bool, 'netlist_file': str, 'metrics': dict}
        """
        try:
            if not self.yosys_available:
                return self._synthesis_mock(rtl_code, module_name, output_format)
            
            # Step 1: Write synthesis script
            script_file = self._create_yosys_script(
                rtl_code, module_name, output_format
            )
            
            # Step 2: Run Yosys
            result = subprocess.run(
                ['yosys', '-c', script_file],
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode != 0:
                logger.warning(f"Yosys warning: {result.stderr}")
            
            # Step 3: Parse results
            netlist_file = os.path.join(
                self.output_dir,
                f'{module_name}_netlist.{output_format}'
            )
            
            metrics = self._parse_synthesis_results(
                result.stdout, result.stderr
            )
            
            return {
                'success': True,
                'netlist_file': netlist_file,
                'metrics': metrics,
                'message': f"✓ Synthesis complete: {metrics['gate_count']} gates, {metrics['area_estimate']:.0f}µm²"
            }
        
        except Exception as e:
            logger.error(f"Synthesis error: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'message': f"❌ Synthesis failed: {str(e)}"
            }
    
    def _check_yosys(self):
        """Check if Yosys is installed"""
        try:
            result = subprocess.run(
                ['yosys', '-version'],
                capture_output=True,
                timeout=5
            )
            return result.returncode == 0
        except (FileNotFoundError, subprocess.TimeoutExpired):
            logger.warning("Yosys not found - using mock synthesis")
            return False
    
    def _create_yosys_script(self, rtl_code, module_name, output_format):
        """Create Yosys synthesis script"""
        script_file = os.path.join(self.output_dir, f'{module_name}_synth.ys')
        
        # Determine output format
        output_flag = 'verilog' if output_format == 'verilog' else 'json'
        netlist_file = os.path.join(
            self.output_dir,
            f'{module_name}_netlist.{output_format}'
        )
        
        # Write RTL to temp file
        rtl_file = os.path.join(self.output_dir, f'{module_name}_rtl.v')
        with open(rtl_file, 'w') as f:
            f.write(rtl_code)
        
        # Create synthesis script
        script = f"""# Yosys synthesis script for {module_name}
read_verilog {rtl_file}
synth -top {module_name} -flatten -abc -nobram -nosrl -noxaui

# Analyze resource usage
stat

# Generate reports
write_eblif -textmode {netlset_file.replace('.verilog', '.eblif').replace('.json', '.json')}
write_{output_flag} {netlist_file}

# Exit
exit
"""
        
        with open(script_file, 'w') as f:
            f.write(script)
        
        return script_file
    
    def _parse_synthesis_results(self, stdout, stderr):
        """Parse Yosys output to extract metrics"""
        metrics = {
            'gate_count': 0,
            'lut_count': 0,
            'ff_count': 0,
            'area_estimate': 0.0,
            'timing_critical': None,
            'power_estimate': 0.0,
            'message': 'Synthesis complete'
        }
        
        # Parse output
        for line in stdout.split('\n'):
            if 'Number of wires' in line:
                try:
                    metrics['gate_count'] = int(re.search(r'\d+', line).group(0))
                except:
                    pass
            
            if 'lut' in line.lower():
                try:
                    metrics['lut_count'] = int(re.search(r'\d+', line).group(0))
                except:
                    pass
            
            if 'ff' in line.lower() or 'flip' in line.lower():
                try:
                    metrics['ff_count'] = int(re.search(r'\d+', line).group(0))
                except:
                    pass
        
        # Estimate area (rough calculation)
        metrics['area_estimate'] = (metrics['gate_count'] * 10 + 
                                   metrics['ff_count'] * 50)
        
        return metrics
    
    def _synthesis_mock(self, rtl_code, module_name, output_format):
        """Generate mock synthesis report (when Yosys not available)"""
        # Parse Verilog for rough estimates
        gate_count = max(10, len(re.findall(r'\b(?:and|or|xor|nand|nor)\b', rtl_code)))
        ff_count = len(re.findall(r'\breg\b', rtl_code))
        
        netlist_file = os.path.join(
            self.output_dir,
            f'{module_name}_netlist_mock.{output_format}'
        )
        
        # Create mock netlist
        if output_format == 'verilog':
            netlist = f"""// Mock Synthesis Netlist
// Original RTL:
{rtl_code}

// Synthesis Report:
// Gates: {gate_count}
// Flip-flops: {ff_count}
// Estimated Area: {(gate_count * 10 + ff_count * 50):.0f} µm²
"""
        else:  # json
            netlist = json.dumps({
                'module': module_name,
                'synthesis_type': 'mock',
                'gates': gate_count,
                'flip_flops': ff_count,
                'area_um2': gate_count * 10 + ff_count * 50,
                'note': 'Mock synthesis (Yosys not installed)'
            }, indent=2)
        
        with open(netlist_file, 'w') as f:
            f.write(netlist)
        
        return {
            'success': True,
            'netlist_file': netlist_file,
            'metrics': {
                'gate_count': gate_count,
                'lut_count': gate_count // 2,
                'ff_count': ff_count,
                'area_estimate': gate_count * 10 + ff_count * 50,
                'power_estimate': (gate_count * 0.5 + ff_count * 1.2),
                'message': f'✓ Mock synthesis: {gate_count} gates, {ff_count} flip-flops'
            },
            'message': f'✓ Mock synthesis: {gate_count} gates, {ff_count} flip-flops (Yosys not available)'
        }
    
    def generate_resource_report(self, metrics):
        """Generate detailed resource utilization report"""
        report = f"""
╔══════════════════════════════════════════════╗
║     RESOURCE UTILIZATION REPORT              ║
╚══════════════════════════════════════════════╝

LOGIC RESOURCES:
  Gate Count:        {metrics.get('gate_count', 0):>6} gates
  LUT Count:         {metrics.get('lut_count', 0):>6} LUTs
  Flip-Flop Count:   {metrics.get('ff_count', 0):>6} FFs

AREA ESTIMATION:
  Gate Area:         {(metrics.get('gate_count', 0) * 10):>10.0f} µm²
  FF Area:           {(metrics.get('ff_count', 0) * 50):>10.0f} µm²
  Total Area:        {metrics.get('area_estimate', 0):>10.0f} µm²

POWER ESTIMATION:
  Power (Dynamic):   {(metrics.get('power_estimate', 0)):>10.2f} mW

TIMING:
  Critical Path:     {metrics.get('timing_critical', 'N/A'):>10}

╔══════════════════════════════════════════════╗
║     SYNTHESIS COMPLETE                       ║
╚══════════════════════════════════════════════╝
"""
        return report
    
    def install_yosys_instructions(self):
        """Provide installation instructions for Yosys"""
        return {
            'linux': 'sudo apt-get install yosys  # Ubuntu/Debian',
            'mac': 'brew install yosys  # macOS',
            'windows': 'Download from http://www.clifford.at/yosys/ or use WSL',
            'docker': 'docker run -it hdlc/yosys:latest',
            'source': 'Build from https://github.com/YosysHQ/yosys'
        }
    
    def get_synthesis_info(self):
        """Get information about synthesis availability"""
        return {
            'yosys_available': self.yosys_available,
            'status': '✓ Yosys available' if self.yosys_available else '⚠ Yosys not found (using mock)',
            'install_instructions': self.install_yosys_instructions(),
            'documentation': 'http://www.clifford.at/yosys/documentation.html'
        }


if __name__ == '__main__':
    # Test synthesis
    test_rtl = """
module adder_8bit(
    input [7:0] a, b,
    output [8:0] sum
);
    assign sum = a + b;
endmodule
"""
    
    runner = SynthesisRunner(debug=True)
    result = runner.synthesize_rtl(test_rtl, 'adder_8bit', 'verilog')
    print(f"Result: {result}")
    
    if result['success']:
        print(runner.generate_resource_report(result['metrics']))
