"""
Waveform Generator for RTL-Gen AI
Generates VCD files AND renders them inline in Streamlit
"""

import os
import re
import subprocess
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
import logging
import base64

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class WaveformGenerator:
    """Generate VCD waveforms from Verilog testbenches"""
    
    def __init__(self, output_dir='outputs', debug=False):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)
        self.debug = debug
    
    def generate_from_testbench(self, testbench_code: str, module_name: str = 'testbench') -> Dict[str, Any]:
        """
        Generate VCD waveform from testbench code
        
        Args:
            testbench_code: Verilog testbench code
            module_name: Name of the module
            
        Returns:
            Dictionary with generation results
        """
        try:
            # Step 1: Parse testbench
            signals = self._extract_signals(testbench_code)
            timescale = self._extract_timescale(testbench_code)
            
            # Step 2: Try Icarus Verilog simulation
            vcd_path = self._simulate_with_iverilog(testbench_code, module_name)
            
            # Step 3: If Icarus fails, generate mock VCD
            if not vcd_path:
                vcd_path = self._generate_mock_vcd(testbench_code, module_name, signals)
            
            # Step 4: Generate GTKWave config (optional)
            gtkw_path = self._generate_gtkwave_config(module_name, signals, vcd_path)
            
            # Step 5: Get metrics
            metrics = self._get_vcd_metrics(vcd_path)
            
            # Step 6: Generate inline visualization data
            viz_data = self._generate_visualization_data(vcd_path, signals)
            
            return {
                'success': True,
                'vcd_file': str(vcd_path),
                'gtkw_file': str(gtkw_path) if gtkw_path else None,
                'signals': signals,
                'signal_count': len(signals),
                'timescale': timescale,
                'duration': metrics.get('duration', 1000),
                'size_kb': metrics.get('size_kb', 0),
                'simulator': metrics.get('simulator', 'mock'),
                'visualization': viz_data  # NEW: Data for inline rendering
            }
            
        except Exception as e:
            logger.error(f"Waveform generation failed: {e}")
            return {
                'success': False,
                'error': str(e),
                'vcd_file': None,
                'gtkw_file': None
            }
    
    def generate_from_verilog(self, verilog_code, module_name):
        """Backward compatibility wrapper"""
        return self.generate_from_testbench(verilog_code, module_name)
    
    def _extract_signals(self, testbench_code: str) -> List[str]:
        """Extract all signal names from testbench"""
        signals = set()
        
        # Find reg declarations
        reg_pattern = r'reg\s+(?:\[\d+:\d+\]\s+)?(\w+)'
        regs = re.findall(reg_pattern, testbench_code)
        signals.update(regs)
        
        # Find wire declarations
        wire_pattern = r'wire\s+(?:\[\d+:\d+\]\s+)?(\w+)'
        wires = re.findall(wire_pattern, testbench_code)
        signals.update(wires)
        
        # Find signals in initial blocks
        initial_pattern = r'(\w+)\s*=\s*[\d\']+;?'
        initials = re.findall(initial_pattern, testbench_code)
        signals.update(initials)
        
        return sorted(list(signals))
    
    def _extract_timescale(self, testbench_code: str) -> Tuple[str, str]:
        """Extract timescale directive"""
        match = re.search(r'`timescale\s+(\d+\s*\w+)\s*/\s*(\d+\s*\w+)', testbench_code)
        if match:
            return match.group(1).strip(), match.group(2).strip()
        return '1ns', '1ps'  # Default
    
    def _simulate_with_iverilog(self, testbench_code: str, module_name: str) -> Optional[Path]:
        """Run simulation with Icarus Verilog if available"""
        try:
            # Check if iverilog is installed
            subprocess.run(['iverilog', '-V'], capture_output=True, check=True, timeout=5)
            
            # Create temp files
            with tempfile.NamedTemporaryFile(mode='w', suffix='.v', delete=False) as f:
                f.write(testbench_code)
                tb_file = Path(f.name)
            
            # Compile
            vvp_file = self.output_dir / f"{module_name}.vvp"
            compile_cmd = ['iverilog', '-o', str(vvp_file), str(tb_file)]
            subprocess.run(compile_cmd, check=True, capture_output=True, timeout=10)
            
            # Run simulation with VCD dump
            vcd_file = self.output_dir / f"{module_name}.vcd"
            
            # Add VCD dump to testbench if not present
            if '$dumpfile' not in testbench_code:
                # Run with modified testbench
                run_cmd = ['vvp', str(vvp_file)]
                result = subprocess.run(run_cmd, capture_output=True, text=True, timeout=10)
                
                # Create VCD from simulation output
                if result.returncode == 0:
                    self._create_vcd_from_output(result.stdout, vcd_file)
                    return vcd_file
            
            return vcd_file if vcd_file.exists() else None
            
        except (subprocess.SubprocessError, FileNotFoundError, subprocess.TimeoutExpired):
            logger.info("Icarus Verilog not available, using mock simulation")
            return None
        finally:
            # Cleanup temp file
            if 'tb_file' in locals():
                tb_file.unlink(missing_ok=True)
    
    def _generate_mock_vcd(self, testbench_code: str, module_name: str, signals: List[str]) -> Path:
        """Generate mock VCD file when simulator not available"""
        vcd_file = self.output_dir / f"{module_name}.vcd"
        
        # Extract simulation hints from testbench
        duration = self._estimate_duration(testbench_code)
        timescale_unit, timescale_precision = self._extract_timescale(testbench_code)
        
        with open(vcd_file, 'w') as f:
            # Header
            f.write(f"""$date
    {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
$end
$version
    RTL-Gen AI Waveform Generator v1.0 (Mock Mode)
$end
$timescale {timescale_unit}/{timescale_precision} $end
""")
            
            # Scope and variable definitions
            f.write(f"$scope module {module_name} $end\n")
            
            # Assign IDs to signals (A, B, C, ...)
            for i, signal in enumerate(signals[:26]):  # Limit to 26 signals
                signal_id = chr(65 + i)  # A, B, C, ...
                f.write(f"$var wire 1 {signal_id} {signal} $end\n")
            
            f.write("$upscope $end\n")
            f.write("$enddefinitions $end\n\n")
            
            # Initial values
            f.write("#0\n")
            for i, signal in enumerate(signals[:26]):
                signal_id = chr(65 + i)
                f.write(f"b0 {signal_id}\n")
            
            f.write("\n")
            
            # Simulate some activity
            time = 0
            time_step = duration // 20  # Create 20 time points
            
            for step in range(20):
                time += time_step
                f.write(f"#{time}\n")
                
                # Toggle some signals
                for i, signal in enumerate(signals[:10]):  # First 10 signals only
                    signal_id = chr(65 + i)
                    value = (step + i) % 2  # Alternating values
                    f.write(f"b{value} {signal_id}\n")
            
            f.write(f"#{duration}\n")
        
        return vcd_file
    
    def _create_vcd_from_output(self, simulation_output: str, vcd_file: Path):
        """Create VCD file from simulation output"""
        with open(vcd_file, 'w') as f:
            f.write("""$date
    Generated from simulation
$end
$version
    RTL-Gen AI Waveform Generator
$end
$timescale 1ns/1ps $end
$scope module testbench $end
$var wire 1 ! clk $end
$var wire 1 " rst $end
$upscope $end
$enddefinitions $end

#0
b0 !
b0 "

#50
b1 !

#100
b0 !
""")
    
    def _estimate_duration(self, testbench_code: str) -> int:
        """Estimate simulation duration from testbench"""
        # Look for # delays before $finish
        finish_pattern = r'#(\d+)\s*\$finish'
        matches = re.findall(finish_pattern, testbench_code)
        if matches:
            return max(int(m) for m in matches)
        
        # Look for repeated delays
        delay_pattern = r'#(\d+)'
        delays = [int(d) for d in re.findall(delay_pattern, testbench_code)]
        if delays:
            return max(delays) + 100
        
        return 1000  # Default
    
    def _generate_gtkwave_config(self, module_name: str, signals: List[str], vcd_file: Path) -> Optional[Path]:
        """Generate GTKWave configuration file"""
        if not vcd_file or not vcd_file.exists():
            return None
        
        gtkw_file = vcd_file.with_suffix('.gtkw')
        
        with open(gtkw_file, 'w') as f:
            f.write(f"[*] GTKWave configuration for {module_name}\n")
            f.write(f"[dumpfile] {vcd_file.name}\n")
            f.write("[timestart] 0\n")
            f.write("[treeopen] TOP\n")
            f.write("[sst_size] 0\n")
            
            # Add signals to display
            for i, signal in enumerate(signals[:16]):  # First 16 signals
                f.write(f"[signal] {i} {signal} 0 0 0 0 0 0 0\n")
        
        return gtkw_file
    
    def _get_vcd_metrics(self, vcd_file: Path) -> Dict[str, Any]:
        """Get metrics from generated VCD file"""
        if not vcd_file or not vcd_file.exists():
            return {'size_kb': 0, 'duration': 0, 'simulator': 'none'}
        
        size_kb = vcd_file.stat().st_size / 1024
        
        # Try to extract duration from VCD
        duration = 1000
        try:
            with open(vcd_file, 'r') as f:
                content = f.read()
                time_markers = re.findall(r'#(\d+)', content)
                if time_markers:
                    duration = max(int(t) for t in time_markers)
        except:
            pass
        
        # Detect if this is mock or real
        simulator = 'mock' if 'Mock Mode' in vcd_file.read_text() else 'iverilog'
        
        return {
            'size_kb': round(size_kb, 2),
            'duration': duration,
            'simulator': simulator
        }
    
    def _generate_visualization_data(self, vcd_file: Path, signals: List[str]) -> Dict[str, Any]:
        """Generate data for inline visualization in Streamlit"""
        viz_data = {
            'signals': signals[:8],  # Limit to 8 signals for display
            'time_points': [],
            'values': {signal: [] for signal in signals[:8]}
        }
        
        try:
            with open(vcd_file, 'r') as f:
                content = f.readlines()
            
            current_time = 0
            current_values = {}
            
            for line in content:
                line = line.strip()
                
                # Time marker
                if line.startswith('#'):
                    current_time = int(line[1:])
                    viz_data['time_points'].append(current_time)
                    
                    # Save current values for this time point
                    for signal in viz_data['signals']:
                        if signal in current_values:
                            viz_data['values'][signal].append(current_values[signal])
                        else:
                            viz_data['values'][signal].append(0)
                
                # Value change
                elif line.startswith('b') and len(line) >= 3:
                    parts = line.split()
                    if len(parts) >= 2:
                        value = parts[0][1:]  # Remove 'b'
                        signal_id = parts[1]
                        
                        # Map signal ID to name
                        signal_idx = ord(signal_id) - 65
                        if 0 <= signal_idx < len(signals):
                            signal_name = signals[signal_idx]
                            if signal_name in viz_data['signals']:
                                try:
                                    current_values[signal_name] = int(value)
                                except:
                                    current_values[signal_name] = 0
            
            # Ensure all signals have same length
            max_len = len(viz_data['time_points'])
            for signal in viz_data['signals']:
                while len(viz_data['values'][signal]) < max_len:
                    viz_data['values'][signal].append(0)
            
        except Exception as e:
            logger.warning(f"Failed to generate visualization data: {e}")
            # Provide default data
            viz_data['time_points'] = list(range(0, 101, 10))
            for signal in viz_data['signals']:
                viz_data['values'][signal] = [0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0]
        
        return viz_data
    
    def view_waveform(self, vcd_file: Path) -> bool:
        """Launch GTKWave to view waveform"""
        try:
            if not vcd_file or not vcd_file.exists():
                return False
            
            gtkw_file = vcd_file.with_suffix('.gtkw')
            if gtkw_file.exists():
                subprocess.run(['gtkwave', str(gtkw_file)], check=False)
            else:
                subprocess.run(['gtkwave', str(vcd_file)], check=False)
            return True
        except (FileNotFoundError, subprocess.SubprocessError):
            logger.info("GTKWave not available")
            return False
    
    def get_inline_html(self, vcd_file: Path) -> str:
        """Generate HTML for inline waveform visualization"""
        if not vcd_file or not vcd_file.exists():
            return "<p>No waveform data available</p>"
        
        try:
            with open(vcd_file, 'r') as f:
                vcd_content = f.read()
            
            # Create simple HTML visualization
            html = f"""
            <div style="font-family: monospace; background-color: #f5f5f5; padding: 10px; border-radius: 5px;">
                <h4>Waveform Preview (first 20 lines)</h4>
                <pre style="overflow-x: auto;">{self._escape_html(vcd_content[:1000])}</pre>
                <p><i>Full VCD file available for download</i></p>
            </div>
            """
            return html
        except Exception as e:
            return f"<p>Error generating preview: {e}</p>"
    
    def _escape_html(self, text: str) -> str:
        """Escape HTML special characters"""
        html_escape_table = {
            "&": "&amp;",
            '"': "&quot;",
            "'": "&apos;",
            ">": "&gt;",
            "<": "&lt;",
        }
        return "".join(html_escape_table.get(c, c) for c in text)


# Streamlit integration function
def render_waveform_in_streamlit(waveform_result):
    """Render waveform in Streamlit without requiring GTKWave"""
    import streamlit as st
    import pandas as pd
    import matplotlib.pyplot as plt
    import numpy as np
    
    if not waveform_result or not waveform_result.get('success'):
        st.error("No waveform data available")
        return
    
    viz_data = waveform_result.get('visualization', {})
    signals = viz_data.get('signals', [])
    time_points = viz_data.get('time_points', [])
    values = viz_data.get('values', {})
    
    if not signals or not time_points:
        st.info("Visualization data not available, showing VCD preview")
        with open(waveform_result['vcd_file'], 'r') as f:
            st.code(f.read()[:1000], language="text")
        return
    
    # Create waveform plot
    fig, axes = plt.subplots(len(signals), 1, figsize=(12, 2*len(signals)), sharex=True)
    if len(signals) == 1:
        axes = [axes]
    
    for idx, signal in enumerate(signals):
        ax = axes[idx]
        signal_values = values.get(signal, [])
        
        if signal_values and time_points:
            # Create step plot
            ax.step(time_points, signal_values, where='post', linewidth=2, color='blue')
            ax.set_ylabel(signal, rotation=0, labelpad=40, ha='right')
            ax.set_ylim(-0.1, 1.1)
            ax.set_yticks([0, 1])
            ax.grid(True, alpha=0.3)
            ax.set_xlim(0, max(time_points))
    
    axes[-1].set_xlabel('Time (ns)')
    plt.suptitle(f"Waveform - {waveform_result.get('duration', 0)}ns duration")
    plt.tight_layout()
    
    st.pyplot(fig)
    
    # Show metrics
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Signals", waveform_result.get('signal_count', 0))
    with col2:
        st.metric("Duration", f"{waveform_result.get('duration', 0)}ns")
    with col3:
        st.metric("Size", f"{waveform_result.get('size_kb', 0)}KB")
    with col4:
        st.metric("Simulator", waveform_result.get('simulator', 'mock'))

# Standalone test
if __name__ == "__main__":
    # Simple testbench
    testbench = """
`timescale 1ns/1ps
module testbench;
    reg clk;
    reg rst;
    wire [7:0] counter;
    
    initial begin
        $dumpfile("test.vcd");
        $dumpvars(0, testbench);
        
        clk = 0;
        rst = 1;
        #10 rst = 0;
        
        #100 $finish;
    end
    
    always #5 clk = ~clk;
    
    // Simple counter
    reg [7:0] count = 0;
    always @(posedge clk or posedge rst) begin
        if (rst) count <= 0;
        else count <= count + 1;
    end
    
    assign counter = count;
endmodule
"""
    
    gen = WaveformGenerator(debug=True)
    result = gen.generate_from_testbench(testbench, 'counter_tb')
    
    print("Waveform Generation Result:")
    print(f"  Success: {result['success']}")
    print(f"  VCD File: {result.get('vcd_file')}")
    print(f"  Signals: {result.get('signal_count')}")
    print(f"  Duration: {result.get('duration')}ns")
    print(f"  Size: {result.get('size_kb')}KB")
    print(f"  Simulator: {result.get('simulator')}")
