`timescale 1ns/1ps

module counter_4bit_tb;
    reg clk;
    reg rst;
    reg en;
    wire [3:0] count;

    integer pass_count = 0;
    integer fail_count = 0;

    counter_4bit dut (
        .clk(clk),
        .rst(rst),
        .en(en),
        .count(count)
    );

    initial clk = 0;
    always #5 clk = ~clk;

    task automatic check_count;
        input [3:0] expected;
        input [127:0] label;
        begin
            @(posedge clk);
            #1;
            if (count === expected) begin
                $display("PASS %0s: count=%0d", label, count);
                pass_count = pass_count + 1;
            end else begin
                $display("FAIL %0s: count=%0d expected=%0d", label, count, expected);
                fail_count = fail_count + 1;
            end
        end
    endtask

    initial begin
        $dumpfile("trace.vcd");
        $dumpvars(0, counter_4bit_tb);

        rst = 1;
        en = 0;
        check_count(4'd0, "reset_holds_zero");

        rst = 0;
        en = 1;
        check_count(4'd1, "increment_1");
        check_count(4'd2, "increment_2");
        check_count(4'd3, "increment_3");
        check_count(4'd4, "increment_4");

        en = 0;
        check_count(4'd4, "hold_when_disabled");

        if (fail_count == 0)
            $display("ALL_TESTS_PASSED");
        else
            $display("TESTS_FAILED");

        #10;
        $finish;
    end
endmodule
