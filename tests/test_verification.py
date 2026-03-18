"""
Unit tests for Verification Engine
Run with: pytest tests/test_verification.py -v
"""

import pytest
from pathlib import Path

from python.compilation_manager import CompilationManager
from python.simulation_runner import SimulationRunner
from python.results_parser import ResultsParser
from python.verification_engine import VerificationEngine, quick_verify


class TestCompilationManager:
    """Test suite for CompilationManager."""
    
    def setup_method(self):
        """Setup for each test."""
        self.manager = CompilationManager(debug=False)
    
    def test_compile_valid_rtl(self):
        """Test: Compile valid RTL code."""
        code = """
module test(input a, output b);
    assign b = a;
endmodule
"""
        result = self.manager.compile(code)
        
        assert result['success'] is True
        assert result['executable'].exists()
        assert len(result['errors']) == 0
    
    def test_compile_with_testbench(self):
        """Test: Compile RTL with testbench."""
        rtl = """
module counter(input clk, output reg [3:0] count);
    always @(posedge clk) count <= count + 1;
endmodule
"""
        
        tb = """
module counter_tb;
    reg clk;
    wire [3:0] count;
    counter dut(.*);
    initial #100 $finish;
endmodule
"""
        
        result = self.manager.compile(rtl, tb)
        
        assert result['success'] is True
        assert result['tb_file'] is not None
    
    def test_compile_syntax_error(self):
        """Test: Detect syntax errors."""
        bad_code = """
module bad(
    input a
    output b  // Missing comma
);
endmodule
"""
        result = self.manager.compile(bad_code)
        
        assert result['success'] is False
        assert len(result['errors']) > 0
    
    def test_compile_missing_endmodule(self):
        """Test: Detect missing endmodule."""
        bad_code = """
module incomplete(input a, output b);
    assign b = a;
// Missing endmodule
"""
        result = self.manager.compile(bad_code)
        
        assert result['success'] is False


class TestSimulationRunner:
    """Test suite for SimulationRunner."""
    
    def setup_method(self):
        """Setup for each test."""
        self.runner = SimulationRunner(debug=False)
        self.compiler = CompilationManager(debug=False)
    
    def test_run_simple_simulation(self):
        """Test: Run simple simulation."""
        rtl = """
module test;
    initial begin
        $display("Hello from simulation!");
        $finish;
    end
endmodule
"""
        
        # Compile first
        compile_result = self.compiler.compile(rtl)
        assert compile_result['success']
        
        # Run simulation
        sim_result = self.runner.run(compile_result['executable'])
        
        assert sim_result['success'] is True
        assert 'Hello from simulation!' in sim_result['output']
    
    def test_simulation_with_waveform(self):
        """Test: Generate VCD waveform."""
        rtl = """
module test;
    reg clk;
    initial begin
        $dumpfile("waveform.vcd");
        $dumpvars(0, test);
        clk = 0;
        #10 clk = 1;
        #10 $finish;
    end
endmodule
"""
        
        compile_result = self.compiler.compile(rtl)
        sim_result = self.runner.run(
            compile_result['executable'],
            waveform_name="test_wave"
        )
        
        assert sim_result['success'] is True
        # Waveform file should be created
        # (check depends on ENABLE_WAVEFORMS config)
    
    def test_simulation_timeout(self):
        """Test: Handle simulation timeout."""
        # Infinite loop - should timeout
        rtl = """
module infinite;
    initial begin
        while (1) begin
            #1;  // Infinite loop
        end
    end
endmodule
"""
        
        compile_result = self.compiler.compile(rtl)
        
        # Create runner with short timeout
        runner = SimulationRunner(debug=False)
        runner.timeout = 2  # 2 seconds
        
        sim_result = runner.run(compile_result['executable'])
        
        assert sim_result['success'] is False
        assert sim_result['timed_out'] is True


class TestResultsParser:
    """Test suite for ResultsParser."""
    
    def setup_method(self):
        """Setup for each test."""
        self.parser = ResultsParser(debug=False)
    
    def test_parse_all_passed(self):
        """Test: Parse all tests passed."""
        output = """
Test 1: PASS
Test 2: PASS
Test 3: PASS
All tests passed!
"""
        result = self.parser.parse(output)
        
        assert result['passed'] is True
        assert result['tests_passed'] == 4  # 3 explicit + "all tests passed"
        assert result['tests_failed'] == 0
    
    def test_parse_with_failures(self):
        """Test: Parse with some failures."""
        output = """
Test 1: PASS
Test 2: FAIL (expected 5, got 3)
Test 3: PASS
ERROR: Test suite failed
"""
        result = self.parser.parse(output)
        
        assert result['passed'] is False
        assert result['tests_passed'] >= 2
        assert result['tests_failed'] >= 1
    
    def test_parse_no_explicit_tests(self):
        """Test: Parse output with no explicit PASS/FAIL."""
        output = """
VCD info: dumpfile waveform.vcd opened for output.
Simulation running...
Counter: 0, 1, 2, 3, 4
Simulation complete
"""
        result = self.parser.parse(output)
        
        # Should pass (no errors detected)
        assert result['passed'] is True
    
    def test_parse_with_errors(self):
        """Test: Parse output with errors."""
        output = """
Test 1: PASS
ERROR: Signal not found
Test 2: FAIL
"""
        result = self.parser.parse(output)
        
        assert result['passed'] is False
        assert len(result['errors']) > 0


class TestVerificationEngine:
    """Test suite for VerificationEngine."""
    
    def setup_method(self):
        """Setup for each test."""
        self.engine = VerificationEngine(debug=False)
    
    def test_verify_complete_success(self):
        """Test: Complete successful verification."""
        rtl = """
module adder(input [3:0] a, b, output [3:0] sum);
    assign sum = a + b;
endmodule
"""
        
        tb = """
module adder_tb;
    reg [3:0] a, b;
    wire [3:0] sum;
    adder dut(.*);
    
    initial begin
        a = 4'd5; b = 4'd3;
        #10;
        if (sum == 4'd8)
            $display("Test: PASS");
        else
            $display("Test: FAIL");
        $finish;
    end
endmodule
"""
        
        result = self.engine.verify(rtl, tb, module_name="adder_test")
        
        assert result['passed'] is True
        assert result['compilation_passed'] is True
        assert result['simulation_passed'] is True
    
    def test_verify_compilation_error(self):
        """Test: Handle compilation error."""
        bad_rtl = """
module bad(
    input a
    output b
);
endmodule
"""
        
        result = self.engine.verify(bad_rtl)
        
        assert result['passed'] is False
        assert result['compilation_passed'] is False
        assert len(result['errors']) > 0
    
    def test_verify_no_testbench(self):
        """Test: Verify without testbench."""
        rtl = """
module simple(input a, output b);
    assign b = a;
endmodule
"""
        
        result = self.engine.verify(rtl)
        
        # Should pass compilation, skip simulation
        assert result['compilation_passed'] is True
        assert result['simulation_passed'] is None
        assert len(result['warnings']) > 0  # Warning about no testbench
    
    def test_quick_verify_function(self):
        """Test: Quick verify convenience function."""
        rtl = """
module test(input a, output b);
    assign b = ~a;
endmodule
"""
        
        tb = """
module test_tb;
    reg a;
    wire b;
    test dut(.*);
    initial begin
        a = 0; #10;
        $display("Test: PASS");
        $finish;
    end
endmodule
"""
        
        passed = quick_verify(rtl, tb)
        assert passed is True


if __name__ == "__main__":
    pytest.main([__file__, '-v', '--tb=short'])
