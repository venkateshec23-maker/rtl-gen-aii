"""
Port Analyzer for RTL-Gen AI
Analyzes Verilog module ports to determine testbench requirements.

Features:
1. Parse module declaration
2. Extract port names and widths
3. Identify special signals (clock, reset)
4. Determine design type hints

Usage:
    analyzer = PortAnalyzer()
    info = analyzer.analyze(verilog_code)
    print(info['inputs'])
    print(info['outputs'])
"""

import re
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass

from python.config import DEBUG_MODE


@dataclass
class Port:
    """Represents a port in a Verilog module."""
    name: str
    direction: str  # 'input', 'output', 'inout'
    width: int = 1  # Bit width (1 for single bit)
    is_vector: bool = False
    is_clock: bool = False
    is_reset: bool = False


class PortAnalyzer:
    """
    Analyzes Verilog module ports.
    
    Extracts:
    - Module name
    - Input ports (with widths)
    - Output ports (with widths)
    - Special signals (clock, reset)
    
    Usage:
        analyzer = PortAnalyzer()
        info = analyzer.analyze(verilog_code)
    """
    
    def __init__(self, debug: bool = None):
        """
        Initialize port analyzer.
        
        Args:
            debug: Enable debug output
        """
        self.debug = debug if debug is not None else DEBUG_MODE
        
        # Patterns for clock/reset detection
        self.clock_names = ['clk', 'clock', 'CLK', 'CLOCK']
        self.reset_names = ['rst', 'reset', 'RST', 'RESET', 'rst_n', 'reset_n']
        
        if self.debug:
            print("PortAnalyzer initialized")
    
    def analyze(self, verilog_code: str) -> Dict:
        """
        Analyze Verilog module.
        
        Args:
            verilog_code: Verilog source code
            
        Returns:
            dict: {
                'module_name': str,
                'inputs': list[Port],
                'outputs': list[Port],
                'has_clock': bool,
                'has_reset': bool,
                'total_input_bits': int,
                'total_output_bits': int,
            }
        """
        if self.debug:
            print("\nAnalyzing Verilog module...")
        
        # Extract module name
        module_name = self._extract_module_name(verilog_code)
        
        if not module_name:
            raise ValueError("Could not find module declaration")
        
        if self.debug:
            print(f"  Module: {module_name}")
        
        # Extract ports
        inputs, outputs = self._extract_ports(verilog_code)
        
        # Identify special signals
        has_clock = any(p.is_clock for p in inputs)
        has_reset = any(p.is_reset for p in inputs)
        
        # Calculate total bits
        total_input_bits = sum(p.width for p in inputs)
        total_output_bits = sum(p.width for p in outputs)
        
        if self.debug:
            print(f"  Inputs: {len(inputs)} ({total_input_bits} bits)")
            for port in inputs:
                print(f"    - {port.name} [{port.width}]" + 
                      (" (clock)" if port.is_clock else "") +
                      (" (reset)" if port.is_reset else ""))
            
            print(f"  Outputs: {len(outputs)} ({total_output_bits} bits)")
            for port in outputs:
                print(f"    - {port.name} [{port.width}]")
        
        return {
            'module_name': module_name,
            'inputs': inputs,
            'outputs': outputs,
            'has_clock': has_clock,
            'has_reset': has_reset,
            'total_input_bits': total_input_bits,
            'total_output_bits': total_output_bits,
        }
    
    def _extract_module_name(self, code: str) -> Optional[str]:
        """Extract module name from code."""
        match = re.search(r'module\s+(\w+)', code, re.IGNORECASE)
        if match:
            return match.group(1)
        return None
    
    def _extract_ports(self, code: str) -> Tuple[List[Port], List[Port]]:
        """
        Extract input and output ports.
        
        Returns:
            tuple: (inputs, outputs)
        """
        inputs = []
        outputs = []
        
        # Pattern 1: ANSI-style ports (Verilog-2001)
        # module name(input [7:0] a, output [7:0] b);
        ansi_pattern = r'(input|output|inout)\s+(?:(?:wire|reg)\s+)?(?:\[(\d+):(\d+)\]\s+)?(\w+)'
        
        for match in re.finditer(ansi_pattern, code, re.IGNORECASE):
            direction = match.group(1).lower()
            msb = match.group(2)
            lsb = match.group(3)
            name = match.group(4)
            
            # Calculate width
            if msb and lsb:
                width = int(msb) - int(lsb) + 1
                is_vector = True
            else:
                width = 1
                is_vector = False
            
            # Check if clock or reset
            is_clock = name in self.clock_names
            is_reset = name in self.reset_names
            
            port = Port(
                name=name,
                direction=direction,
                width=width,
                is_vector=is_vector,
                is_clock=is_clock,
                is_reset=is_reset,
            )
            
            if direction == 'input':
                inputs.append(port)
            elif direction == 'output':
                outputs.append(port)
        
        return inputs, outputs
    
    def suggest_design_type(self, analysis: Dict) -> str:
        """
        Suggest design type based on ports.
        
        Args:
            analysis: Result from analyze()
            
        Returns:
            str: 'combinational', 'sequential', or 'fsm'
        """
        if analysis['has_clock']:
            # Has clock → sequential or FSM
            # Simple heuristic: if few states, sequential, else FSM
            return 'sequential'
        else:
            return 'combinational'


# ============================================================================
# SELF-TEST
# ============================================================================

if __name__ == "__main__":
    print("Port Analyzer Self-Test\n")
    print("=" * 70)
    
    analyzer = PortAnalyzer(debug=True)
    
    # Test 1: Combinational (adder)
    print("\n1. Testing combinational (adder):")
    print("-" * 70)
    
    code1 = """
module adder_8bit(
    input [7:0] a,
    input [7:0] b,
    output [7:0] sum,
    output carry
);
    assign {carry, sum} = a + b;
endmodule
"""
    
    result1 = analyzer.analyze(code1)
    print(f"\nModule: {result1['module_name']}")
    print(f"Has clock: {result1['has_clock']}")
    print(f"Type: {analyzer.suggest_design_type(result1)}")
    
    # Test 2: Sequential (counter)
    print("\n2. Testing sequential (counter):")
    print("-" * 70)
    
    code2 = """
module counter(
    input clk,
    input reset,
    input enable,
    output reg [7:0] count
);
    always @(posedge clk) begin
        if (reset)
            count <= 8'd0;
        else if (enable)
            count <= count + 1;
    end
endmodule
"""
    
    result2 = analyzer.analyze(code2)
    print(f"\nModule: {result2['module_name']}")
    print(f"Has clock: {result2['has_clock']}")
    print(f"Has reset: {result2['has_reset']}")
    print(f"Type: {analyzer.suggest_design_type(result2)}")
    
    print("\n" + "=" * 70)
    print("Self-test complete!")
    print("=" * 70)
