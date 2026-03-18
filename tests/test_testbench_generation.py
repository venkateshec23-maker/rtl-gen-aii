"""
Unit tests for Testbench Generation
Run with: pytest tests/test_testbench_generation.py -v
"""

import pytest
from pathlib import Path

from python.port_analyzer import PortAnalyzer, Port
from python.test_vector_generator import TestVectorGenerator
from python.testbench_generator import TestbenchGenerator
from python.verification_engine import VerificationEngine


class TestPortAnalyzer:
    """Test suite for PortAnalyzer."""
    
    def setup_method(self):
        """Setup for each test."""
        self.analyzer = PortAnalyzer(debug=False)
    
    def test_analyze_simple_module(self):
        """Test: Analyze simple combinational module."""
        code = """
module test(
    input [7:0] a,
    input [7:0] b,
    output [7:0] sum
);
    assign sum = a + b;
endmodule
"""
        result = self.analyzer.analyze(code)
        
        assert result['module_name'] == 'test'
        assert len(result['inputs']) == 2
        assert len(result['outputs']) == 1
        assert result['inputs'][0].width == 8
        assert result['has_clock'] is False
    
    def test_analyze_sequential_module(self):
        """Test: Analyze sequential module with clock."""
        code = """
module counter(
    input clk,
    input reset,
    output reg [7:0] count
);
    always @(posedge clk) begin
        if (reset)
            count <= 0;
        else
            count <= count + 1;
    end
endmodule
"""
        result = self.analyzer.analyze(code)
        
        assert result['has_clock'] is True
        assert result['has_reset'] is True
        assert len(result['inputs']) == 2
    
    def test_suggest_design_type(self):
        """Test: Suggest design type based on ports."""
        # Combinational
        code1 = "module test(input a, output b); assign b = a; endmodule"
        result1 = self.analyzer.analyze(code1)
        assert self.analyzer.suggest_design_type(result1) == 'combinational'
        
        # Sequential
        code2 = "module test(input clk, output reg b); always @(posedge clk) b <= 1; endmodule"
        result2 = self.analyzer.analyze(code2)
        assert self.analyzer.suggest_design_type(result2) == 'sequential'


class TestTestVectorGenerator:
    """Test suite for TestVectorGenerator."""
    
    def setup_method(self):
        """Setup for each test."""
        self.generator = TestVectorGenerator(debug=False)
    
    def test_exhaustive_small_inputs(self):
        """Test: Exhaustive generation for small inputs."""
        inputs = [
            Port('a', 'input', width=2),
            Port('b', 'input', width=2),
        ]
        
        vectors = self.generator.generate(inputs, strategy='exhaustive')
        
        # Should have 4*4 = 16 combinations
        assert len(vectors) == 16
        
        # Check all values are present
        values_a = set(v['a'] for v in vectors)
        values_b = set(v['b'] for v in vectors)
        assert values_a == {0, 1, 2, 3}
        assert values_b == {0, 1, 2, 3}
    
    def test_auto_strategy_selection(self):
        """Test: Auto strategy selection based on input size."""
        # Small inputs → exhaustive
        small_inputs = [Port('a', 'input', width=4)]
        vectors1 = self.generator.generate(small_inputs, strategy='auto')
        assert len(vectors1) == 16  # 2^4
        
        # Large inputs → directed
        large_inputs = [
            Port('a', 'input', width=9),
            Port('b', 'input', width=8),
        ]
        vectors2 = self.generator.generate(large_inputs, strategy='auto')
        # Should be less than exhaustive (2^16 = 65536)
        assert len(vectors2) < 1000
    
    def test_corner_cases(self):
        """Test: Generate corner cases."""
        inputs = [
            Port('a', 'input', width=4),
            Port('b', 'input', width=4),
        ]
        
        vectors = self.generator.generate(inputs, strategy='corners')
        
        # Should include all zeros and all max
        assert {'a': 0, 'b': 0} in vectors
        assert {'a': 15, 'b': 15} in vectors
        
        # Should have reasonable number of corners
        assert len(vectors) >= 4
        assert len(vectors) <= 10
    
    def test_random_generation(self):
        """Test: Random test vector generation."""
        inputs = [Port('a', 'input', width=8)]
        
        vectors = self.generator.generate(inputs, strategy='random')
        
        # Should generate default count
        assert len(vectors) == 100
        
        # All values should be in valid range
        for vec in vectors:
            assert 0 <= vec['a'] <= 255


class TestTestbenchGenerator:
    """Test suite for TestbenchGenerator."""
    
    def setup_method(self):
        """Setup for each test."""
        self.generator = TestbenchGenerator(debug=False)
    
    def test_generate_combinational_tb(self):
        """Test: Generate testbench for combinational circuit."""
        rtl = """
module adder(
    input [3:0] a,
    input [3:0] b,
    output [3:0] sum,
    output carry
);
    assign {carry, sum} = a + b;
endmodule
"""
        
        result = self.generator.generate(rtl, design_type='combinational')
        
        assert result['success'] is True
        assert 'adder_tb' in result['testbench_code']
        assert 'initial begin' in result['testbench_code']
        assert '$finish' in result['testbench_code']
        assert result['test_count'] > 0
    
    def test_generate_sequential_tb(self):
        """Test: Generate testbench for sequential circuit."""
        rtl = """
module counter(
    input clk,
    input reset,
    output reg [3:0] count
);
    always @(posedge clk) begin
        if (reset)
            count <= 0;
        else
            count <= count + 1;
    end
endmodule
"""
        
        result = self.generator.generate(rtl, design_type='sequential')
        
        assert result['success'] is True
        assert 'clk = 0' in result['testbench_code']  # Clock generation
        assert 'reset' in result['testbench_code']  # Reset sequence
        assert '@(posedge clk)' in result['testbench_code']  # Clock sync
    
    def test_auto_type_detection(self):
        """Test: Auto-detect design type."""
        # Should detect combinational
        comb_rtl = "module test(input a, output b); assign b = a; endmodule"
        result1 = self.generator.generate(comb_rtl, design_type='auto')
        assert result1['success'] is True
        
        # Should detect sequential
        seq_rtl = """
module test(input clk, output reg b);
    always @(posedge clk) b <= 1;
endmodule
"""
        result2 = self.generator.generate(seq_rtl, design_type='auto')
        assert result2['success'] is True
        assert 'clk = 0' in result2['testbench_code']


# Removed TestIntegration because relies on prompt_builder and input_processor from Day 7+ skipped days.

if __name__ == "__main__":
    pytest.main([__file__, '-v', '--tb=short'])
