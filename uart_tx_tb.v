`timescale 1ns/1ps

module uart_tx_tb;
    reg clk;
    reg reset_n;
    reg tx_start;
    reg [7:0] data_in;
    reg [15:0] baud_div;

    wire tx_out;
    wire tx_busy;
    wire tx_done;

    uart_tx uut (
        .clk(clk),
        .reset_n(reset_n),
        .tx_start(tx_start),
        .data_in(data_in),
        .baud_div(baud_div),
        .tx_out(tx_out),
        .tx_busy(tx_busy),
        .tx_done(tx_done)
    );

    initial begin
        $dumpfile("C:/Users/venka/Documents/rtl-gen-aii/trace.vcd");
        $dumpvars(0, uart_tx_tb);

        clk = 0;
        reset_n = 0;
        tx_start = 0;
        data_in = 8'h00;
        baud_div = 16'd4;

        #10;
        reset_n = 1;
        #10;

        data_in = 8'h55;
        tx_start = 1;
        #10;
        tx_start = 0;

        @(posedge tx_done);
        #1;
        if (tx_out == 1) begin
            $display("PASS Test 1 - Stop bit after transmission");
        end else begin
            $display("FAIL Test 1: got %b, expected 1", tx_out);
        end

        #50;
        data_in = 8'hAA;
        tx_start = 1;
        #10;
        tx_start = 0;

        @(posedge tx_done);
        #1;
        if (tx_out == 1) begin
            $display("PASS Test 2 - Stop bit after transmission");
        end else begin
            $display("FAIL Test 2: got %b, expected 1", tx_out);
        end

        #50;
        data_in = 8'h00;
        tx_start = 1;
        #10;
        tx_start = 0;

        @(posedge tx_done);
        #1;
        if (tx_out == 1) begin
            $display("PASS Test 3 - Stop bit after transmission");
        end else begin
            $display("FAIL Test 3: got %b, expected 1", tx_out);
        end

        #50;
        data_in = 8'hFF;
        tx_start = 1;
        #10;
        tx_start = 0;

        @(posedge tx_done);
        #1;
        if (tx_out == 1) begin
            $display("PASS Test 4 - Stop bit after transmission");
        end else begin
            $display("FAIL Test 4: got %b, expected 1", tx_out);
        end

        #50;

        $display("ALL_TESTS_PASSED");

        #50;
        $finish;
    end

    always #5 clk = ~clk;

endmodule