"""
Compilation Manager for RTL-Gen AI
Handles compilation of Verilog code using Icarus Verilog.

Features:
1. Compile Verilog files with iverilog
2. Parse compilation errors
3. Handle multiple source files
4. Detect syntax and semantic errors

Usage:
    manager = CompilationManager()
    result = manager.compile(rtl_code, testbench_code)
    
    if result['success']:
        print("Compilation successful!")
    else:
        print("Errors:", result['errors'])
"""

import subprocess
import tempfile
import re
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from python.config import (
    IVERILOG_PATH,
    SIM_WORKSPACE,
    DEBUG_MODE,
)


class CompilationManager:
    """
    Manages Verilog code compilation.
    
    Workflow:
    1. Write source files to temporary directory
    2. Invoke iverilog compiler
    3. Capture stdout/stderr
    4. Parse errors and warnings
    5. Return compilation result
    
    Usage:
        manager = CompilationManager()
        result = manager.compile(rtl_code, testbench_code)
    """
    
    def __init__(self, debug: bool = None):
        """
        Initialize compilation manager.
        
        Args:
            debug: Enable debug output
        """
        self.debug = debug if debug is not None else DEBUG_MODE
        self.iverilog_path = IVERILOG_PATH
        self.workspace = SIM_WORKSPACE
        
        if self.debug:
            print(f"CompilationManager initialized")
            print(f"  Compiler: {self.iverilog_path}")
            print(f"  Workspace: {self.workspace}")
    
    def compile(self, rtl_code: str, testbench_code: str = None,
                output_name: str = "simulation") -> Dict:
        """
        Compile Verilog code.
        
        Args:
            rtl_code: RTL module code
            testbench_code: Testbench code (optional)
            output_name: Name for output executable
            
        Returns:
            dict: {
                'success': bool,
                'executable': Path (if successful),
                'rtl_file': Path,
                'tb_file': Path (if testbench provided),
                'errors': list,
                'warnings': list,
                'output': str (compiler output),
            }
        """
        if self.debug:
            print("\nCompiling Verilog code...")
        
        errors = []
        warnings = []
        
        # Step 1: Write source files
        try:
            rtl_file = self.workspace / "rtl.v"
            rtl_file.write_text(rtl_code, encoding='utf-8')
            
            if self.debug:
                print(f"  Wrote RTL: {rtl_file}")
            
            source_files = [str(rtl_file)]
            
            if testbench_code:
                tb_file = self.workspace / "testbench.v"
                tb_file.write_text(testbench_code, encoding='utf-8')
                source_files.append(str(tb_file))
                
                if self.debug:
                    print(f"  Wrote TB: {tb_file}")
            else:
                tb_file = None
        
        except Exception as e:
            return {
                'success': False,
                'executable': None,
                'rtl_file': None,
                'tb_file': None,
                'errors': [f"Failed to write source files: {e}"],
                'warnings': [],
                'output': "",
            }
        
        # Step 2: Prepare compilation command
        executable = self.workspace / f"{output_name}.out"
        
        compile_cmd = [
            self.iverilog_path,
            '-o', str(executable),
            '-g2012',  # Use SystemVerilog-2012 standard
        ] + source_files
        
        if self.debug:
            print(f"  Command: {' '.join(compile_cmd)}")
        
        # Step 3: Run compilation
        try:
            result = subprocess.run(
                compile_cmd,
                capture_output=True,
                text=True,
                timeout=30,
                cwd=str(self.workspace),
            )
            
            output = result.stdout + result.stderr
            
            if self.debug:
                print(f"  Return code: {result.returncode}")
                if output:
                    print(f"  Output:\n{output}")
            
            # Step 4: Parse errors and warnings
            errors, warnings = self._parse_compiler_output(output)
            
            # Step 5: Check if compilation succeeded
            success = (result.returncode == 0) and executable.exists()
            
            return {
                'success': success,
                'executable': executable if success else None,
                'rtl_file': rtl_file,
                'tb_file': tb_file,
                'errors': errors,
                'warnings': warnings,
                'output': output,
            }
        
        except subprocess.TimeoutExpired:
            return {
                'success': False,
                'executable': None,
                'rtl_file': rtl_file,
                'tb_file': tb_file,
                'errors': ["Compilation timeout (> 30 seconds)"],
                'warnings': [],
                'output': "",
            }
        
        except Exception as e:
            return {
                'success': False,
                'executable': None,
                'rtl_file': rtl_file,
                'tb_file': tb_file,
                'errors': [f"Compilation failed: {e}"],
                'warnings': [],
                'output': "",
            }
    
    def _parse_compiler_output(self, output: str) -> Tuple[List[str], List[str]]:
        """
        Parse compiler output for errors and warnings.
        
        Icarus Verilog error format:
        - filename:line: syntax error
        - filename:line: warning: message
        - filename:line: error: message
        
        Args:
            output: Compiler stdout/stderr
            
        Returns:
            tuple: (errors, warnings)
        """
        errors = []
        warnings = []
        
        for line in output.split('\n'):
            line = line.strip()
            if not line:
                continue
            
            # Check for errors
            if 'error:' in line.lower() or 'syntax error' in line.lower():
                errors.append(line)
            
            # Check for warnings
            elif 'warning:' in line.lower():
                warnings.append(line)
            
            # Check for other error indicators
            elif 'cannot' in line.lower() or 'undefined' in line.lower():
                errors.append(line)
        
        return errors, warnings


# ============================================================================
# SELF-TEST
# ============================================================================

if __name__ == "__main__":
    print("Compilation Manager Self-Test\n")
    print("=" * 70)
    
    manager = CompilationManager(debug=True)
    
    # Test 1: Valid code
    print("\n1. Testing valid code:")
    print("-" * 70)
    
    rtl_code = """
module adder(
    input [7:0] a, b,
    output [7:0] sum,
    output carry
);
    assign {carry, sum} = a + b;
endmodule
"""
    
    tb_code = """
module adder_tb;
    reg [7:0] a, b;
    wire [7:0] sum;
    wire carry;
    
    adder dut(.*);
    
    initial begin
        $display("Testing adder");
        a = 8'd5; b = 8'd3;
        #10;
        $display("5 + 3 = %d (carry=%b)", sum, carry);
        $finish;
    end
endmodule
"""
    
    result = manager.compile(rtl_code, tb_code)
    
    print(f"\nSuccess: {result['success']}")
    print(f"Errors: {result['errors']}")
    print(f"Warnings: {result['warnings']}")
    
    if result['success']:
        print(f"Executable: {result['executable']}")
    
    # Test 2: Invalid code (syntax error)
    print("\n2. Testing invalid code (syntax error):")
    print("-" * 70)
    
    bad_code = """
module broken(
    input a, b
    output c  // Missing comma!
);
    assign c = a & b;
endmodule
"""
    
    result2 = manager.compile(bad_code)
    
    print(f"\nSuccess: {result2['success']}")
    print(f"Errors found: {len(result2['errors'])}")
    for error in result2['errors']:
        print(f"  - {error}")
    
    print("\n" + "=" * 70)
    print("Self-test complete!")
    print("=" * 70)
