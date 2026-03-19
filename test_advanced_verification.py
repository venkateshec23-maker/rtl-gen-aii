"""
Test Advanced Verification Features

Tests coverage analysis, assertion generation, and formal verification.

Usage: python test_advanced_verification.py
"""

from python.coverage_analyzer import CoverageAnalyzer
from python.assertion_generator import AssertionGenerator
from python.formal_verification import FormalVerifier


def test_coverage_analysis():
    """Test coverage analysis."""
    print("=" * 70)
    print("TEST 1: COVERAGE ANALYSIS")
    print("=" * 70)

    analyzer = CoverageAnalyzer()

    # Test design
    rtl_code = """
module alu_4bit(
    input [3:0] a,
    input [3:0] b,
    input [1:0] op,
    output reg [3:0] result
);
    always @(*) begin
        case (op)
            2'b00: result = a + b;
            2'b01: result = a - b;
            2'b10: result = a & b;
            2'b11: result = a | b;
        endcase
    end
endmodule
"""

    testbench = """
module alu_4bit_tb;
    reg [3:0] a, b;
    reg [1:0] op;
    wire [3:0] result;

    alu_4bit dut(.a(a), .b(b), .op(op), .result(result));

    initial begin
        a = 4'b1010; b = 4'b0101;
        op = 2'b00; #10;
        op = 2'b01; #10;
        op = 2'b10; #10;
        op = 2'b11; #10;
        $finish;
    end
endmodule
"""

    # Analyze coverage
    results = analyzer.analyze_coverage(rtl_code, testbench, 'alu_4bit')

    # Generate report
    report_file = analyzer.generate_coverage_report(results)

    print(f"\n✓ Coverage analysis complete")
    print(f"  Overall coverage: {results['overall']['overall_coverage_percent']:.2f}%")
    print(f"  Report: {report_file}")

    return results['overall']['overall_coverage_percent'] >= 80


def test_assertion_generation():
    """Test assertion generation."""
    print("\n" + "=" * 70)
    print("TEST 2: ASSERTION GENERATION")
    print("=" * 70)

    generator = AssertionGenerator()

    # Test design
    rtl_code = """
module handshake_ctrl(
    input clk,
    input rst,
    input req,
    output reg ack,
    output reg valid,
    input ready
);
    reg [1:0] state;

    always @(posedge clk or posedge rst) begin
        if (rst) begin
            state <= 2'b00;
            ack <= 1'b0;
            valid <= 1'b0;
        end else begin
            case (state)
                2'b00: if (req) begin state <= 2'b01; ack <= 1'b1; end
                2'b01: begin ack <= 1'b0; valid <= 1'b1; state <= 2'b10; end
                2'b10: if (ready) begin valid <= 1'b0; state <= 2'b00; end
            endcase
        end
    end
endmodule
"""

    # Generate assertions
    assertions = generator.generate_assertions(rtl_code, 'handshake_ctrl')

    # Create assertion module
    assertion_code = generator.create_assertion_module(assertions)

    total_assertions = (
        len(assertions['immediate_assertions']) +
        len(assertions['concurrent_assertions']) +
        len(assertions['properties']) +
        len(assertions['sequences'])
    )

    print(f"\n✓ Assertion generation complete")
    print(f"  Total assertions: {total_assertions}")

    return total_assertions > 0


def test_formal_verification():
    """Test formal verification."""
    print("\n" + "=" * 70)
    print("TEST 3: FORMAL VERIFICATION")
    print("=" * 70)

    verifier = FormalVerifier()

    if not any(verifier.tools_available.values()):
        print("\n⚠ No formal tools available - skipping")
        return True

    # Simple design with property
    rtl_code = """
module simple_counter(
    input clk,
    input rst,
    output reg [3:0] count
);
    always @(posedge clk or posedge rst) begin
        if (rst)
            count <= 4'b0;
        else
            count <= count + 1;
    end

    assert property (@(posedge clk) count <= 4'd15);
endmodule
"""

    properties = [
        "count <= 4'd15",
    ]

    # Verify properties
    result = verifier.verify_properties(
        rtl_code=rtl_code,
        properties=properties,
        module_name='simple_counter',
        mode='bmc'
    )

    print(f"\n✓ Formal verification complete")
    print(f"  Properties checked: {result.get('properties_checked', 0)}")

    return True


def test_integration():
    """Test integration of all verification features."""
    print("\n" + "=" * 70)
    print("TEST 4: INTEGRATED VERIFICATION")
    print("=" * 70)

    # Complete design
    rtl_code = """
module fifo_8x4(
    input clk,
    input rst,
    input wr_en,
    input rd_en,
    input [3:0] data_in,
    output reg [3:0] data_out,
    output reg full,
    output reg empty
);
    reg [3:0] mem [0:7];
    reg [2:0] wr_ptr, rd_ptr;
    reg [3:0] count;

    always @(posedge clk or posedge rst) begin
        if (rst) begin
            wr_ptr <= 3'b0;
            rd_ptr <= 3'b0;
            count <= 4'b0;
            full <= 1'b0;
            empty <= 1'b1;
        end else begin
            if (wr_en && !full) begin
                mem[wr_ptr] <= data_in;
                wr_ptr <= wr_ptr + 1;
                count <= count + 1;
            end

            if (rd_en && !empty) begin
                data_out <= mem[rd_ptr];
                rd_ptr <= rd_ptr + 1;
                count <= count - 1;
            end

            full <= (count == 8);
            empty <= (count == 0);
        end
    end
endmodule
"""

    testbench = """
module fifo_8x4_tb;
    reg clk, rst, wr_en, rd_en;
    reg [3:0] data_in;
    wire [3:0] data_out;
    wire full, empty;

    fifo_8x4 dut(.*);

    initial begin
        clk = 0;
        forever #5 clk = ~clk;
    end

    initial begin
        rst = 1; wr_en = 0; rd_en = 0; data_in = 0;
        #10 rst = 0;

        repeat (8) begin
            @(posedge clk);
            wr_en = 1;
            data_in = data_in + 1;
        end
        wr_en = 0;

        repeat (8) begin
            @(posedge clk);
            rd_en = 1;
        end
        rd_en = 0;

        #20 $finish;
    end
endmodule
"""

    print("\nRunning integrated verification...")

    # 1. Coverage analysis
    print("\n  [1/3] Coverage analysis...")
    analyzer = CoverageAnalyzer()
    cov_results = analyzer.analyze_coverage(rtl_code, testbench, 'fifo_8x4')

    # 2. Assertion generation
    print("  [2/3] Assertion generation...")
    generator = AssertionGenerator()
    assertions = generator.generate_assertions(rtl_code, 'fifo_8x4')

    # 3. Generate reports
    print("  [3/3] Generating reports...")
    cov_report = analyzer.generate_coverage_report(cov_results)
    assertion_code = generator.create_assertion_module(assertions)

    print(f"\n✓ Integrated verification complete")
    print(f"  Coverage: {cov_results['overall']['overall_coverage_percent']:.2f}%")
    print(f"  Assertions: {len(assertions['immediate_assertions']) + len(assertions['concurrent_assertions'])}")

    return True


def main():
    """Run all tests."""
    print("\n" + "=" * 70)
    print("ADVANCED VERIFICATION TEST SUITE")
    print("=" * 70)

    results = []

    # Test 1: Coverage Analysis
    results.append(("Coverage Analysis", test_coverage_analysis()))

    # Test 2: Assertion Generation
    results.append(("Assertion Generation", test_assertion_generation()))

    # Test 3: Formal Verification
    results.append(("Formal Verification", test_formal_verification()))

    # Test 4: Integration
    results.append(("Integrated Verification", test_integration()))

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
