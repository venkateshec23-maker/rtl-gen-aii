"""
Assertion Generator for RTL-Gen AI
Generates SystemVerilog assertions for testbenches.

Usage:
    generator = AssertionGenerator()
    assertions = generator.generate(inputs, outputs)
"""

from typing import List, Dict
from python.port_analyzer import Port


class AssertionGenerator:
    """Generate SystemVerilog assertions."""
    
    def generate_range_assertions(self, outputs: List[Port]) -> List[str]:
        """
        Generate range check assertions.
        
        Args:
            outputs: Output ports
            
        Returns:
            list: Assertion code lines
        """
        assertions = []
        
        for port in outputs:
            if port.is_vector:
                max_val = (1 << port.width) - 1
                assertion = f"""
    // Range check for {port.name}
    assert property (@(posedge clk) {port.name} <= {max_val})
        else $error("Range violation: {port.name} = %d", {port.name});
"""
                assertions.append(assertion)
        
        return assertions
    
    def generate_stability_assertions(self, signals: List[str]) -> List[str]:
        """
        Generate stability assertions (signal shouldn't change unexpectedly).
        
        Args:
            signals: Signal names to check
            
        Returns:
            list: Assertion code lines
        """
        assertions = []
        
        for signal in signals:
            assertion = f"""
    // Stability check for {signal}
    property {signal}_stable;
        @(posedge clk) disable iff (reset)
        $stable({signal});
    endproperty
"""
            assertions.append(assertion)
        
        return assertions


# Test
if __name__ == "__main__":
    generator = AssertionGenerator()
    
    outputs = [Port('sum', 'output', width=8)]
    assertions = generator.generate_range_assertions(outputs)
    
    for assertion in assertions:
        print(assertion)
