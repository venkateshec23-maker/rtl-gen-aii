from verilog_generator import (
    validate_testbench_has_real_checks,
    inject_real_checks_into_testbench
)

# Test 1: Lying testbench
lying_tb = '''
module adder_tb();
reg [7:0] a, b;
wire [8:0] sum;
adder dut(.a(a),.b(b),.sum(sum));
initial clk = 0;
always #5 clk = ~clk;
initial begin
    a = 8'hFF; b = 8'h01;
    @(posedge clk); #1;
    $display("ALL_TESTS_PASSED");
    $finish;
end
endmodule
'''

result = validate_testbench_has_real_checks(lying_tb)
print('Is lying:', result['is_lying'])
print('Issues:', result['issues'])
print('Verdict:', result['verdict'])

# Test 2: Honest testbench
honest_tb = '''
module adder_tb();
reg [7:0] a, b;
wire [8:0] sum;
integer fail_count = 0;
adder dut(.a(a),.b(b),.sum(sum));
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
'''

result2 = validate_testbench_has_real_checks(honest_tb)
print()
print('Is lying:', result2['is_lying'])
print('Verdict:', result2['verdict'])
