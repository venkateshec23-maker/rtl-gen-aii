"""
Coverage Generator for RTL-Gen AI
Generates SystemVerilog coverage code.

Usage:
    generator = CoverageGenerator()
    coverage = generator.generate(inputs, outputs)
"""

from typing import List
from python.port_analyzer import Port


class CoverageGenerator:
    """Generate SystemVerilog coverage code."""
    
    def generate_covergroups(self, inputs: List[Port], outputs: List[Port]) -> str:
        """
        Generate covergroup for inputs and outputs.
        
        Args:
            inputs: Input ports
            outputs: Output ports
            
        Returns:
            str: SystemVerilog covergroup code
        """
        coverpoints = []
        
        # Cover inputs
        for port in inputs:
            if not port.is_clock and not port.is_reset:
                if port.is_vector:
                    coverpoints.append(f"        {port.name}_cp: coverpoint {port.name};")
                else:
                    coverpoints.append(f"        {port.name}_cp: coverpoint {port.name};")
        
        # Cover outputs
        for port in outputs:
            if port.is_vector:
                coverpoints.append(f"        {port.name}_cp: coverpoint {port.name};")
            else:
                coverpoints.append(f"        {port.name}_cp: coverpoint {port.name};")
        
        covergroup = f"""
    // Coverage
    covergroup cg @(posedge clk);
{chr(10).join(coverpoints)}
    endgroup
    
    cg cg_inst = new();
"""
        return covergroup


# Test
if __name__ == "__main__":
    generator = CoverageGenerator()
    
    inputs = [Port('a', 'input', width=4), Port('b', 'input', width=4)]
    outputs = [Port('sum', 'output', width=4)]
    
    coverage = generator.generate_covergroups(inputs, outputs)
    print(coverage)
