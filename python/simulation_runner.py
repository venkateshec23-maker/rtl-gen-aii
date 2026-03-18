"""
Simulation Runner for RTL-Gen AI
Executes compiled Verilog simulations using vvp.

Features:
1. Run simulations with timeout
2. Capture simulation output
3. Generate VCD waveforms
4. Handle runtime errors

Usage:
    runner = SimulationRunner()
    result = runner.run(executable_path)
    
    if result['success']:
        print("Simulation completed!")
        print(result['output'])
"""

import subprocess
from pathlib import Path
from typing import Dict, Optional

from python.config import (
    VVP_PATH,
    SIMULATION_TIMEOUT,
    ENABLE_WAVEFORMS,
    WAVEFORM_DIR,
    DEBUG_MODE,
)


class SimulationRunner:
    """
    Runs Verilog simulations.
    
    Workflow:
    1. Invoke vvp with executable
    2. Capture stdout/stderr
    3. Handle timeouts
    4. Collect VCD waveform files
    5. Return simulation output
    
    Usage:
        runner = SimulationRunner()
        result = runner.run(executable_path)
    """
    
    def __init__(self, debug: bool = None):
        """
        Initialize simulation runner.
        
        Args:
            debug: Enable debug output
        """
        self.debug = debug if debug is not None else DEBUG_MODE
        self.vvp_path = VVP_PATH
        self.timeout = SIMULATION_TIMEOUT
        self.enable_waveforms = ENABLE_WAVEFORMS
        
        if self.debug:
            print(f"SimulationRunner initialized")
            print(f"  Simulator: {self.vvp_path}")
            print(f"  Timeout: {self.timeout}s")
            print(f"  Waveforms: {self.enable_waveforms}")
    
    def run(self, executable: Path, waveform_name: str = None) -> Dict:
        """
        Run simulation.
        
        Args:
            executable: Path to compiled simulation
            waveform_name: Name for VCD file (optional)
            
        Returns:
            dict: {
                'success': bool,
                'output': str (simulation output),
                'waveform_file': Path (if generated),
                'runtime_seconds': float,
                'errors': list,
                'timed_out': bool,
            }
        """
        if not executable.exists():
            return {
                'success': False,
                'output': "",
                'waveform_file': None,
                'runtime_seconds': 0.0,
                'errors': [f"Executable not found: {executable}"],
                'timed_out': False,
            }
        
        if self.debug:
            print(f"\nRunning simulation: {executable}")
        
        # Prepare simulation command
        sim_cmd = [self.vvp_path, str(executable)]
        
        # Run simulation
        try:
            import time
            start_time = time.time()
            
            result = subprocess.run(
                sim_cmd,
                capture_output=True,
                text=True,
                timeout=self.timeout,
                cwd=str(executable.parent),
            )
            
            runtime = time.time() - start_time
            
            output = result.stdout + result.stderr
            
            if self.debug:
                print(f"  Runtime: {runtime:.2f}s")
                print(f"  Return code: {result.returncode}")
                if output:
                    print(f"  Output:\n{output}")
            
            # Check for VCD waveform file
            waveform_file = None
            if self.enable_waveforms:
                # Look for waveform.vcd in workspace
                vcd_file = executable.parent / "waveform.vcd"
                if vcd_file.exists():
                    # Move to waveform directory
                    if waveform_name:
                        dest_name = f"{waveform_name}.vcd"
                    else:
                        dest_name = vcd_file.name
                    
                    dest = WAVEFORM_DIR / dest_name
                    vcd_file.replace(dest)
                    waveform_file = dest
                    
                    if self.debug:
                        print(f"  Waveform: {waveform_file}")
            
            # Parse for runtime errors
            errors = self._parse_runtime_errors(output)
            
            success = (result.returncode == 0) and len(errors) == 0
            
            return {
                'success': success,
                'output': output,
                'waveform_file': waveform_file,
                'runtime_seconds': runtime,
                'errors': errors,
                'timed_out': False,
            }
        
        except subprocess.TimeoutExpired:
            if self.debug:
                print(f"  TIMEOUT after {self.timeout}s")
            
            return {
                'success': False,
                'output': "",
                'waveform_file': None,
                'runtime_seconds': self.timeout,
                'errors': [f"Simulation timeout (> {self.timeout}s) - possible infinite loop"],
                'timed_out': True,
            }
        
        except Exception as e:
            return {
                'success': False,
                'output': "",
                'waveform_file': None,
                'runtime_seconds': 0.0,
                'errors': [f"Simulation failed: {e}"],
                'timed_out': False,
            }
    
    def _parse_runtime_errors(self, output: str) -> list:
        """
        Parse simulation output for runtime errors.
        
        Common patterns:
        - ERROR: ...
        - Unable to bind ...
        - Unknown module ...
        - Assertion failed ...
        
        Args:
            output: Simulation output
            
        Returns:
            list: Error messages
        """
        errors = []
        
        for line in output.split('\n'):
            line = line.strip()
            
            # Check for error keywords
            if any(keyword in line.lower() for keyword in [
                'error:', 'unable to', 'unknown', 'undefined',
                'assertion failed', 'fatal:'
            ]):
                errors.append(line)
        
        return errors


# ============================================================================
# SELF-TEST
# ============================================================================

if __name__ == "__main__":
    print("Simulation Runner Self-Test\n")
    print("=" * 70)
    
    # First, compile some code
    from python.compilation_manager import CompilationManager
    
    manager = CompilationManager(debug=True)
    
    rtl_code = """
module counter(
    input clk,
    input reset,
    output reg [3:0] count
);
    always @(posedge clk) begin
        if (reset)
            count <= 4'd0;
        else
            count <= count + 1;
    end
endmodule
"""
    
    tb_code = """
module counter_tb;
    reg clk, reset;
    wire [3:0] count;
    
    counter dut(.*);
    
    initial begin
        $dumpfile("waveform.vcd");
        $dumpvars(0, counter_tb);
        
        clk = 0;
        reset = 1;
        #10 reset = 0;
        
        repeat(10) #5 clk = ~clk;
        
        $display("Final count: %d", count);
        $finish;
    end
endmodule
"""
    
    print("\n1. Compiling code:")
    print("-" * 70)
    
    compile_result = manager.compile(rtl_code, tb_code, output_name="counter_sim")
    
    if compile_result['success']:
        print("[PASS] Compilation successful")
        
        # Run simulation
        print("\n2. Running simulation:")
        print("-" * 70)
        
        runner = SimulationRunner(debug=True)
        sim_result = runner.run(
            compile_result['executable'],
            waveform_name="counter_test"
        )
        
        print(f"\nSuccess: {sim_result['success']}")
        print(f"Runtime: {sim_result['runtime_seconds']:.2f}s")
        print(f"Output:\n{sim_result['output']}")
        
        if sim_result['waveform_file']:
            print(f"\nWaveform: {sim_result['waveform_file']}")
    else:
        print("[FAIL] Compilation failed:")
        for error in compile_result['errors']:
            print(f"  - {error}")
    
    print("\n" + "=" * 70)
    print("Self-test complete!")
    print("=" * 70)
