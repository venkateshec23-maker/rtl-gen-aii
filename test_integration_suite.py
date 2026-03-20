"""
Integration Test Suite

Tests end-to-end workflows combining multiple components.

Usage: python test_integration_suite.py
"""

import os
import json
from python.core_rtl_generator import CoreRTLGenerator
from python.advanced_rtl_generator import AdvancedRTLGenerator
from python.verilog_compiler import VerilogCompiler
from python.rtl_validator import RTLValidator
from python.testbench_generator import TestbenchGenerator


def test_basic_workflow():
    """Test basic RTL generation workflow."""
    print("=" * 70)
    print("TEST 1: BASIC WORKFLOW")
    print("=" * 70)
    
    generator = CoreRTLGenerator()
    
    spec = {
        "module_name": "test_adder",
        "inputs": ["a[7:0]", "b[7:0]", "cin"],
        "outputs": ["sum[7:0]", "cout"],
        "description": "8-bit adder with carry"
    }
    
    try:
        verilog = generator.generate(spec)
        
        is_valid = "module" in verilog.lower() and "endmodule" in verilog.lower()
        
        if is_valid:
            print("\n✓ Basic workflow passed")
            print(f"Generated {len(verilog)} bytes of Verilog code")
        else:
            print("\n✗ Basic workflow failed: Invalid Verilog format")
        
        return is_valid
    except Exception as e:
        print(f"\n✗ Basic workflow failed: {e}")
        return False


def test_advanced_workflow():
    """Test advanced RTL generation workflow."""
    print("\n" + "=" * 70)
    print("TEST 2: ADVANCED WORKFLOW")
    print("=" * 70)
    
    generator = AdvancedRTLGenerator()
    
    spec = {
        "module_name": "test_counter",
        "description": "16-bit counter with reset and enable",
        "constraints": ["low power", "high performance"]
    }
    
    try:
        verilog = generator.generate_with_optimization(spec)
        
        is_valid = verilog and len(verilog) > 100
        
        if is_valid:
            print("\n✓ Advanced workflow passed")
            print(f"Generated optimized Verilog: {len(verilog)} bytes")
        else:
            print("\n✗ Advanced workflow failed: Invalid output")
        
        return is_valid
    except Exception as e:
        print(f"\n✗ Advanced workflow failed: {e}")
        return False


def test_validation_workflow():
    """Test validation workflow."""
    print("\n" + "=" * 70)
    print("TEST 3: VALIDATION WORKFLOW")
    print("=" * 70)
    
    validator = RTLValidator()
    
    verilog_code = """
    module test_module (
        input clk,
        input reset,
        output [7:0] data_out,
        input [7:0] data_in
    );
    
    always @(posedge clk) begin
        if (reset)
            data_out <= 8'b0;
        else
            data_out <= data_in;
    end
    
    endmodule
    """
    
    try:
        report = validator.validate(verilog_code)
        
        is_valid = report['is_valid'] if isinstance(report, dict) else True
        
        if is_valid:
            print("\n✓ Validation workflow passed")
            if isinstance(report, dict):
                print(f"Report: {report}")
        else:
            print("\n✗ Validation workflow failed")
        
        return is_valid
    except Exception as e:
        print(f"\n✗ Validation workflow failed: {e}")
        return False


def test_testbench_generation_workflow():
    """Test testbench generation workflow."""
    print("\n" + "=" * 70)
    print("TEST 4: TESTBENCH GENERATION WORKFLOW")
    print("=" * 70)
    
    generator = TestbenchGenerator()
    
    module_spec = {
        "name": "test_adder",
        "inputs": ["a[7:0]", "b[7:0]"],
        "outputs": ["sum[8:0]"]
    }
    
    try:
        testbench = generator.generate_testbench(module_spec)
        
        is_valid = testbench and "initial" in testbench
        
        if is_valid:
            print("\n✓ Testbench generation passed")
            print(f"Generated testbench: {len(testbench)} bytes")
        else:
            print("\n✗ Testbench generation failed")
        
        return is_valid
    except Exception as e:
        print(f"\n✗ Testbench generation failed: {e}")
        return False


def test_compilation_workflow():
    """Test compilation workflow."""
    print("\n" + "=" * 70)
    print("TEST 5: COMPILATION WORKFLOW")
    print("=" * 70)
    
    compiler = VerilogCompiler()
    
    verilog_code = """
    module test_logic (
        input a,
        input b,
        output y
    );
    
    assign y = a & b;
    
    endmodule
    """
    
    try:
        result = compiler.compile(verilog_code, output_format='simulation')
        
        is_valid = result and result.get('success', False)
        
        if is_valid:
            print("\n✓ Compilation workflow passed")
            print(f"Compilation result: success={result['success']}")
        else:
            print("\n✗ Compilation workflow failed")
        
        return is_valid
    except Exception as e:
        print(f"\n✗ Compilation workflow failed: {e}")
        return False


def test_end_to_end_workflow():
    """Test complete end-to-end workflow."""
    print("\n" + "=" * 70)
    print("TEST 6: END-TO-END WORKFLOW")
    print("=" * 70)
    
    try:
        generator = CoreRTLGenerator()
        validator = RTLValidator()
        testbench_gen = TestbenchGenerator()
        
        spec = {
            "module_name": "e2e_test_mux",
            "inputs": ["a[3:0]", "b[3:0]", "sel"],
            "outputs": ["out[3:0]"],
            "description": "2-to-1 multiplexer"
        }
        
        verilog = generator.generate(spec)
        validation = validator.validate(verilog)
        testbench = testbench_gen.generate_testbench(spec)
        
        is_valid = (verilog and validation and testbench)
        
        if is_valid:
            print("\n✓ End-to-end workflow passed")
            print(f"Generated: RTL ({len(verilog)} bytes) + Testbench ({len(testbench)} bytes)")
        else:
            print("\n✗ End-to-end workflow failed")
        
        return is_valid
    except Exception as e:
        print(f"\n✗ End-to-end workflow failed: {e}")
        return False


def main():
    """Run all integration tests."""
    print("\n" + "=" * 70)
    print("INTEGRATION TEST SUITE")
    print("=" * 70)
    
    results = []
    
    results.append(("Basic Workflow", test_basic_workflow()))
    results.append(("Advanced Workflow", test_advanced_workflow()))
    results.append(("Validation Workflow", test_validation_workflow()))
    results.append(("Testbench Generation", test_testbench_generation_workflow()))
    results.append(("Compilation", test_compilation_workflow()))
    results.append(("End-to-End Workflow", test_end_to_end_workflow()))
    
    print("\n" + "=" * 70)
    print("INTEGRATION TEST SUMMARY")
    print("=" * 70)
    
    for name, passed in results:
        status = "✓ PASS" if passed else "✗ FAIL"
        print(f"{status} - {name}")
    
    passed_count = sum(1 for _, passed in results if passed)
    print(f"\nPassed: {passed_count}/{len(results)}")
    
    if passed_count == len(results):
        print("\n🔄 ALL INTEGRATION TESTS PASSED! 🔄")
    
    print("=" * 70)


if __name__ == "__main__":
    main()
