"""Verify lying testbench detection — Task 1 validation script."""

from verilog_generator import (
    validate_testbench_has_real_checks,
    inject_real_checks_into_testbench
)

# Test 1: Lying testbench (no real checks)
lying_tb = r"""
module adder_tb();
reg [7:0] a, b;
wire [8:0] sum;
adder dut(.a(a),.b(b),.sum(sum));
reg clk;
initial clk = 0;
always #5 clk = ~clk;
initial begin
    a = 8'hFF; b = 8'h01;
    @(posedge clk); #1;
    $display("ALL_TESTS_PASSED");
    $finish;
end
endmodule
"""

result = validate_testbench_has_real_checks(lying_tb)
print("=== TEST 1: LYING TESTBENCH ===")
print("Is lying:", result["is_lying"])
print("Issues:", result["issues"])
print("Verdict:", result["verdict"])
assert result["is_lying"] is True, "FAIL: should detect lying testbench"

# Test 2: Honest testbench (has real checks)
honest_tb = r"""
module adder_tb();
reg [7:0] a, b;
wire [8:0] sum;
integer fail_count = 0;
adder dut(.a(a),.b(b),.sum(sum));
reg clk;
initial clk = 0;
always #5 clk = ~clk;
initial begin
    a = 8'hFF; b = 8'h01;
    @(posedge clk); #1;
    if (sum !== 9'd256) begin
        $display("FAIL: got %0d", sum);
        fail_count = fail_count + 1;
    end
    if (fail_count == 0)
        $display("ALL_TESTS_PASSED");
    else
        $display("TESTS_FAILED");
    $finish;
end
endmodule
"""

result2 = validate_testbench_has_real_checks(honest_tb)
print()
print("=== TEST 2: HONEST TESTBENCH ===")
print("Is lying:", result2["is_lying"])
print("Verdict:", result2["verdict"])
assert result2["is_lying"] is False, "FAIL: should detect honest testbench"

# Test 3: Injection fix
print()
print("=== TEST 3: INJECTION FIX ===")
fixed = inject_real_checks_into_testbench(lying_tb, "adder", "module adder(); endmodule")
has_fc = "fail_count" in fixed
has_cond = "if (fail_count == 0)" in fixed
print("Has fail_count:", has_fc)
print("Has conditional PASS:", has_cond)
assert has_fc, "FAIL: injection should add fail_count"
assert has_cond, "FAIL: injection should add conditional pass"

print()
print("=" * 50)
print("ALL TASK 1 VERIFICATIONS PASSED")
print("=" * 50)
