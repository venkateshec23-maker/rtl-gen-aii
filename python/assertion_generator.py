"""
Assertion Generator for RTL-Gen AI
Generates SystemVerilog assertions for testbenches.

Usage:
    generator = AssertionGenerator()
    assertions = generator.generate_assertions(rtl_code, module_name)
"""

from typing import List, Dict
import re
from python.port_analyzer import Port


class AssertionGenerator:
    """Generate SystemVerilog assertions."""
    
    def generate_assertions(self, rtl_code: str, module_name: str) -> Dict:
        """
        Generate assertions from RTL code.
        
        Args:
            rtl_code: RTL code to analyze
            module_name: Module name
            
        Returns:
            dict: Assertions with count and details
        """
        assertions = []
        
        # Extract outputs and generate range assertions
        outputs = self._extract_outputs(rtl_code)
        range_assertions = self.generate_range_assertions(outputs)
        assertions.extend(range_assertions)
        
        # Generate stability assertions for key signals
        signals = self._extract_key_signals(rtl_code)
        stability_assertions = self.generate_stability_assertions(signals)
        assertions.extend(stability_assertions)
        
        # Generate protocol assertions
        protocol_assertions = self._generate_protocol_assertions(rtl_code)
        assertions.extend(protocol_assertions)
        
        return {
            'assertion_count': len(assertions),
            'assertions': assertions,
            'module_name': module_name,
        }
    
    def _extract_outputs(self, rtl_code: str) -> List[Port]:
        """Extract output ports from RTL code."""
        outputs = []
        
        # Find output declarations
        output_pattern = r'output\s+(?:reg\s+)?(?:\[[^\]]*\]\s+)?(\w+)'
        for match in re.finditer(output_pattern, rtl_code):
            port_name = match.group(1)
            
            # Try to extract width
            width_pattern = rf'\[(\d+):0\]\s+{port_name}'
            width_match = re.search(width_pattern, rtl_code)
            width = int(width_match.group(1)) + 1 if width_match else 1
            
            port = Port(port_name, 'output', width=width)
            outputs.append(port)
        
        return outputs
    
    def _extract_key_signals(self, rtl_code: str) -> List[str]:
        """Extract key signals for stability checking."""
        signals = []
        
        # Look for register declarations
        reg_pattern = r'reg\s+(?:\[[^\]]*\]\s+)?(\w+)'
        for match in re.finditer(reg_pattern, rtl_code):
            signals.append(match.group(1))
        
        return signals[:5]  # Limit to first 5 signals
    
    def _generate_protocol_assertions(self, rtl_code: str) -> List[str]:
        """Generate protocol-specific assertions."""
        assertions = []
        
        # Check for handshake protocol
        if 'valid' in rtl_code and 'ready' in rtl_code:
            assertions.append("""
    // Handshake protocol check
    property valid_ready_handshake;
        @(posedge clk) disable iff (reset)
        (valid && ready) |-> (valid_payload_valid);
    endproperty
""")
        
        # Check for request/acknowledge
        if 'request' in rtl_code and 'acknowledge' in rtl_code:
            assertions.append("""
    // Request/Acknowledge protocol
    property req_ack_delay;
        @(posedge clk) (request) |-> ##[1:5] acknowledge;
    endproperty
""")
        
        return assertions

    
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
