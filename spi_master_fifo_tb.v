`timescale 1ns/1ps

module spi_master_fifo_tb;

    reg clk;
    reg reset_n;
    reg [7:0] data_in;
    reg tx_start;
    reg miso;
    wire [7:0] data_out;
    wire tx_done;
    wire sclk;
    wire mosi;
    wire cs_n;

    spi_master_fifo uut (
        .clk(clk),
        .reset_n(reset_n),
        .data_in(data_in),
        .tx_start(tx_start),
        .miso(miso),
        .data_out(data_out),
        .tx_done(tx_done),
        .sclk(sclk),
        .mosi(mosi),
        .cs_n(cs_n)
    );

    initial begin
        $dumpfile("C:/Users/venka/Documents/rtl-gen-aii/trace.vcd");
        $dumpvars(0, spi_master_fifo_tb);

        clk = 0;
        reset_n = 0;
        data_in = 8'h00;
        tx_start = 0;
        miso = 0;

        #10;
        #10;
        reset_n = 1;

        #20;
        data_in = 8'h5A;
        tx_start = 1;
        miso = 0;
        #10;
        tx_start = 0;

        @(posedge tx_done);
        #5;
        if (data_out == 8'h5A) begin
            $display("PASS Test 1");
        end else begin
            $display("FAIL Test 1: got 0x%02h, expected 0x5A", data_out);
        end

        #50;
        data_in = 8'h00;
        tx_start = 1;
        miso = 1;
        #10;
        tx_start = 0;

        @(posedge tx_done);
        #5;
        if (data_out == 8'hff) begin
            $display("PASS Test 2");
        end else begin
            $display("FAIL Test 2: got 0x%02h, expected 0xff", data_out);
        end

        #50;
        data_in = 8'hFF;
        tx_start = 1;
        miso = 0;
        #10;
        tx_start = 0;

        @(posedge tx_done);
        #5;
        if (data_out == 8'h00) begin
            $display("PASS Test 3");
        end else begin
            $display("FAIL Test 3: got 0x%02h, expected 0x00", data_out);
        end

        #50;
        data_in = 8'hAA;
        tx_start = 1;
        miso = 1;
        #10;
        tx_start = 0;

        @(posedge tx_done);
        #5;
        if (data_out == 8'hAA) begin
            $display("ALL_TESTS_PASSED");
        end else begin
            $display("TESTS_FAILED: got 0x%02h, expected 0xAA", data_out);
        end

        #50;
        $finish;
    end

    always #5 clk = ~clk;

endmodule