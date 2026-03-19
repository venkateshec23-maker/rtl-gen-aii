"""
Test Synthesis Integration

Tests complete verification pipeline including synthesis and timing analysis.

Usage: python test_synthesis_integration.py
"""

from python.synthesis_engine import SynthesisEngine
from python.timing_analyzer import TimingAnalyzer
from python.verification_engine import VerificationEngine


def test_synthesis_only():
    """Test synthesis in isolation."""
    print("=" * 70)
    print("TEST 1: SYNTHESIS ONLY")
    print("=" * 70)

    engine = SynthesisEngine()

    if not engine.yosys_available:
        print("\n⚠ Yosys not available - skipping synthesis tests")
        print("Install: apt-get install yosys")
        return False

    # Simple test design
    rtl_code = """
module adder_8bit(
    input [7:0] a,
    input [7:0] b,
    input cin,
    output [7:0] sum,
    output cout
);
    assign {cout, sum} = a + b + cin;
endmodule
"""

    result = engine.synthesize(rtl_code, 'adder_8bit')

    if result['success']:
        print("\n✓ Synthesis test passed")
        print(f"  Gate count: {result['gate_count']}")
        return True
    else:
        print(f"\n✗ Synthesis test failed: {result['message']}")
        return False


def test_timing_analysis():
    """Test timing analysis."""
    print("\n" + "=" * 70)
    print("TEST 2: TIMING ANALYSIS")
    print("=" * 70)

    analyzer = TimingAnalyzer()

    # Sequential design
    rtl_code = """
module counter_16bit(
    input clk,
    input rst,
    input enable,
    output reg [15:0] count
);
    always @(posedge clk or posedge rst) begin
        if (rst)
            count <= 16'b0;
        else if (enable)
            count <= count + 1;
    end
endmodule
"""

    # Test at different frequencies
    frequencies = [50, 100, 200, 500]

    for freq_mhz in frequencies:
        period_ns = 1000.0 / freq_mhz
        result = analyzer.analyze_timing(rtl_code, 'counter_16bit', clock_period_ns=period_ns)

        status = "✓" if result['timing_met'] else "✗"
        print(f"\n  {status} {freq_mhz} MHz: slack = {result['slack_ns']:.2f} ns")

    print("\n✓ Timing analysis test complete")
    return True


def test_complete_verification():
    """Test complete verification pipeline."""
    print("\n" + "=" * 70)
    print("TEST 3: COMPLETE VERIFICATION PIPELINE")
    print("=" * 70)

    verifier = VerificationEngine()

    # Test design with testbench
    rtl_code = """
module mux_2to1_4bit(
    input [3:0] a,
    input [3:0] b,
    input sel,
    output [3:0] y
);
    assign y = sel ? b : a;
endmodule
"""

    testbench = """
`timescale 1ns/1ps

module mux_2to1_4bit_tb;
    reg [3:0] a, b;
    reg sel;
    wire [3:0] y;

    mux_2to1_4bit dut(
        .a(a),
        .b(b),
        .sel(sel),
        .y(y)
    );

    initial begin
        $dumpfile("mux_2to1_4bit.vcd");
        $dumpvars(0, mux_2to1_4bit_tb);

        a = 4'b0011; b = 4'b1100; sel = 0;
        #10;
        if (y !== a) $display("ERROR: sel=0 failed");

        sel = 1;
        #10;
        if (y !== b) $display("ERROR: sel=1 failed");

        $display("Test completed");
        $finish;
    end
endmodule
"""

    # Check if synthesis engine is available
    synth_available = SynthesisEngine().yosys_available

    # Run complete verification
    if hasattr(verifier, 'verify_with_synthesis'):
        result = verifier.verify_with_synthesis(
            rtl_code=rtl_code,
            testbench_code=testbench,
            module_name='mux_2to1_4bit',
            synthesize=synth_available,
            analyze_timing=True,
            clock_period_ns=10.0
        )
    else:
        # Fallback if method doesn't exist yet
        result = verifier.verify(rtl_code, testbench, 'mux_2to1_4bit')

    # Print results
    print("\n" + "=" * 70)
    print("VERIFICATION RESULTS")
    print("=" * 70)

    if isinstance(result.get('syntax'), dict):
        print(f"\nSyntax: {'✓ PASS' if result['syntax']['passed'] else '✗ FAIL'}")
        print(f"Simulation: {'✓ PASS' if result['simulation']['passed'] else '✗ FAIL'}")

        if 'synthesis' in result:
            print(f"Synthesis: {'✓ PASS' if result['synthesis']['success'] else '✗ FAIL'}")
            if result['synthesis']['success']:
                print(f"  Gate count: {result['synthesis']['gate_count']}")

        if 'timing' in result:
            print(f"Timing: {'✓ PASS' if result['timing']['timing_met'] else '✗ FAIL'}")
            if result['timing']['timing_met']:
                print(f"  Slack: {result['timing']['slack_ns']:.2f} ns")

        print(f"\nOverall: {'✓ PASS' if result.get('passed', False) else '✗ FAIL'}")
        return result.get('passed', False)
    else:
        print(f"\nVerification: {'✓ PASS' if result['passed'] else '✗ FAIL'}")
        return result['passed']


def test_performance_benchmarks():
    """Test performance of different designs."""
    print("\n" + "=" * 70)
    print("TEST 4: PERFORMANCE BENCHMARKS")
    print("=" * 70)

    verifier = VerificationEngine()

    # Test different design complexities
    designs = [
        ("Simple", "assign y = a & b;", "combinational"),
        ("Medium", "always @(*) y = a + b;", "combinational"),
        ("Complex", "always @(posedge clk) count <= count + 1;", "sequential"),
    ]

    print("\nDesign Complexity Analysis:")
    print(f"{'Design':<15} {'Timing (ns)':<15}")
    print("-" * 40)

    for name, logic, design_type in designs:
        # Create simple module
        if design_type == "combinational":
            rtl = f"module test(input a, b, output y); {logic} endmodule"
        else:
            rtl = f"module test(input clk, output reg [7:0] count); {logic} endmodule"

        # Timing analysis
        analyzer = TimingAnalyzer()
        timing = analyzer.analyze_timing(rtl, 'test', clock_period_ns=10.0)

        print(f"{name:<15} {timing['critical_path_delay_ns']:<15.2f}")

    print("\n✓ Performance benchmark complete")
    return True


def main():
    """Run all tests."""
    print("\n" + "=" * 70)
    print("SYNTHESIS INTEGRATION TEST SUITE")
    print("=" * 70)

    results = []

    # Test 1: Synthesis
    results.append(("Synthesis", test_synthesis_only()))

    # Test 2: Timing Analysis
    results.append(("Timing Analysis", test_timing_analysis()))

    # Test 3: Complete Verification
    results.append(("Complete Verification", test_complete_verification()))

    # Test 4: Performance Benchmarks
    results.append(("Performance Benchmarks", test_performance_benchmarks()))

    # Print summary
    print("\n" + "=" * 70)
    print("TEST SUMMARY")
    print("=" * 70)

    for name, passed in results:
        status = "✓ PASS" if passed else "✗ FAIL"
        print(f"{status} - {name}")

    passed_count = sum(1 for _, passed in results if passed)
    print(f"\nPassed: {passed_count}/{len(results)}")

    print("=" * 70)


if __name__ == "__main__":
    main()
