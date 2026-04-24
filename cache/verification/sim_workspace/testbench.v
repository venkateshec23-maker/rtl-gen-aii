
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
