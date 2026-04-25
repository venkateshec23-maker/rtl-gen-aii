`timescale 1ns/1ps

module alu_32bit_tb;
    reg         clk;
    reg         rst_n;
    reg  [31:0] a;
    reg  [31:0] b;
    reg  [3:0]  op;
    wire [31:0] result;
    wire        zero;
    wire        carry;
    wire        overflow;

    // Operation codes (must match DUT)
    localparam ADD  = 4'b0000;
    localparam SUB  = 4'b0001;
    localparam AND  = 4'b0010;
    localparam OR   = 4'b0011;
    localparam XOR  = 4'b0100;
    localparam NOT  = 4'b0101;
    localparam SLL  = 4'b0110;
    localparam SRL  = 4'b0111;
    localparam SLT  = 4'b1000;
    localparam SLTU = 4'b1001;

    integer test_count;
    integer pass_count;
    integer fail_count;

    alu_32bit uut (
        .clk(clk),
        .rst_n(rst_n),
        .a(a),
        .b(b),
        .op(op),
        .result(result),
        .zero(zero),
        .carry(carry),
        .overflow(overflow)
    );

    // Clock generation
    initial begin
        clk = 0;
    end
    always #5 clk = ~clk;

    // Test stimulus
    initial begin
        $dumpfile("alu_32bit.vcd");
        $dumpvars(0, alu_32bit_tb);

        test_count = 0;
        pass_count = 0;
        fail_count = 0;

        // Reset
        rst_n = 0;
        a = 0;
        b = 0;
        op = 0;
        @(posedge clk);
        @(posedge clk);
        rst_n = 1;
        @(posedge clk);

        // ============================================
        // Test 1: ADD - Basic addition
        // ============================================
        $display("Test 1: ADD - Basic addition");
        test_count = test_count + 1;
        a = 32'h0000_0005;
        b = 32'h0000_0003;
        op = ADD;
        @(posedge clk);
        @(posedge clk);
        if (result === 32'h0000_0008) begin
            $display("  PASS: 5 + 3 = %h", result);
            pass_count = pass_count + 1;
        end else begin
            $display("  FAIL: Expected 00000008, Got %h", result);
            fail_count = fail_count + 1;
        end

        // ============================================
        // Test 2: ADD - Carry generation
        // ============================================
        $display("Test 2: ADD - Carry generation");
        test_count = test_count + 1;
        a = 32'hFFFF_FFFF;
        b = 32'h0000_0001;
        op = ADD;
        @(posedge clk);
        @(posedge clk);
        if (result === 32'h0000_0000 && carry === 1'b1) begin
            $display("  PASS: FFFFFFFF + 1 = 0 with carry");
            pass_count = pass_count + 1;
        end else begin
            $display("  FAIL: result=%h carry=%b", result, carry);
            fail_count = fail_count + 1;
        end

        // ============================================
        // Test 3: SUB - Basic subtraction
        // ============================================
        $display("Test 3: SUB - Basic subtraction");
        test_count = test_count + 1;
        a = 32'h0000_000A;
        b = 32'h0000_0003;
        op = SUB;
        @(posedge clk);
        @(posedge clk);
        if (result === 32'h0000_0007) begin
            $display("  PASS: 10 - 3 = %h", result);
            pass_count = pass_count + 1;
        end else begin
            $display("  FAIL: Expected 00000007, Got %h", result);
            fail_count = fail_count + 1;
        end

        // ============================================
        // Test 4: SUB - Zero result
        // ============================================
        $display("Test 4: SUB - Zero result");
        test_count = test_count + 1;
        a = 32'h0000_0042;
        b = 32'h0000_0042;
        op = SUB;
        @(posedge clk);
        @(posedge clk);
        if (result === 32'h0000_0000 && zero === 1'b1) begin
            $display("  PASS: 66 - 66 = 0 with zero flag");
            pass_count = pass_count + 1;
        end else begin
            $display("  FAIL: result=%h zero=%b", result, zero);
            fail_count = fail_count + 1;
        end

        // ============================================
        // Test 5: AND - Bitwise AND
        // ============================================
        $display("Test 5: AND - Bitwise AND");
        test_count = test_count + 1;
        a = 32'hFFFF_0000;
        b = 32'h00FF_FF00;
        op = AND;
        @(posedge clk);
        @(posedge clk);
        if (result === 32'h00FF_0000) begin
            $display("  PASS: AND result = %h", result);
            pass_count = pass_count + 1;
        end else begin
            $display("  FAIL: Expected 00FF0000, Got %h", result);
            fail_count = fail_count + 1;
        end

        // ============================================
        // Test 6: OR - Bitwise OR
        // ============================================
        $display("Test 6: OR - Bitwise OR");
        test_count = test_count + 1;
        a = 32'hF0F0_F0F0;
        b = 32'h0F0F_0F0F;
        op = OR;
        @(posedge clk);
        @(posedge clk);
        if (result === 32'hFFFF_FFFF) begin
            $display("  PASS: OR result = %h", result);
            pass_count = pass_count + 1;
        end else begin
            $display("  FAIL: Expected FFFFFFFF, Got %h", result);
            fail_count = fail_count + 1;
        end

        // ============================================
        // Test 7: XOR - Bitwise XOR
        // ============================================
        $display("Test 7: XOR - Bitwise XOR");
        test_count = test_count + 1;
        a = 32'hFFFF_FFFF;
        b = 32'hFFFF_0000;
        op = XOR;
        @(posedge clk);
        @(posedge clk);
        if (result === 32'h0000_FFFF) begin
            $display("  PASS: XOR result = %h", result);
            pass_count = pass_count + 1;
        end else begin
            $display("  FAIL: Expected 0000FFFF, Got %h", result);
            fail_count = fail_count + 1;
        end

        // ============================================
        // Test 8: NOT - Bitwise NOT
        // ============================================
        $display("Test 8: NOT - Bitwise NOT");
        test_count = test_count + 1;
        a = 32'h0000_FFFF;
        op = NOT;
        @(posedge clk);
        @(posedge clk);
        if (result === 32'hFFFF_0000) begin
            $display("  PASS: NOT result = %h", result);
            pass_count = pass_count + 1;
        end else begin
            $display("  FAIL: Expected FFFF0000, Got %h", result);
            fail_count = fail_count + 1;
        end

        // ============================================
        // Test 9: SLL - Shift left logical
        // ============================================
        $display("Test 9: SLL - Shift left logical");
        test_count = test_count + 1;
        a = 32'h0000_0001;
        b = 32'h0000_0004;  // Shift by 4
        op = SLL;
        @(posedge clk);
        @(posedge clk);
        if (result === 32'h0000_0010) begin
            $display("  PASS: 1 << 4 = %h", result);
            pass_count = pass_count + 1;
        end else begin
            $display("  FAIL: Expected 00000010, Got %h", result);
            fail_count = fail_count + 1;
        end

        // ============================================
        // Test 10: SRL - Shift right logical
        // ============================================
        $display("Test 10: SRL - Shift right logical");
        test_count = test_count + 1;
        a = 32'h0000_0010;
        b = 32'h0000_0004;  // Shift by 4
        op = SRL;
        @(posedge clk);
        @(posedge clk);
        if (result === 32'h0000_0001) begin
            $display("  PASS: 16 >> 4 = %h", result);
            pass_count = pass_count + 1;
        end else begin
            $display("  FAIL: Expected 00000001, Got %h", result);
            fail_count = fail_count + 1;
        end

        // ============================================
        // Test 11: SLT - Set less than (signed)
        // ============================================
        $display("Test 11: SLT - Set less than (signed)");
        test_count = test_count + 1;
        a = 32'hFFFF_FFFF;  // -1 (signed)
        b = 32'h0000_0001;  // 1
        op = SLT;
        @(posedge clk);
        @(posedge clk);
        if (result === 32'h0000_0001) begin
            $display("  PASS: -1 < 1 = true, result = %h", result);
            pass_count = pass_count + 1;
        end else begin
            $display("  FAIL: Expected 00000001, Got %h", result);
            fail_count = fail_count + 1;
        end

        // ============================================
        // Test 12: SLTU - Set less than (unsigned)
        // ============================================
        $display("Test 12: SLTU - Set less than (unsigned)");
        test_count = test_count + 1;
        a = 32'h0000_0005;
        b = 32'h0000_000A;
        op = SLTU;
        @(posedge clk);
        @(posedge clk);
        if (result === 32'h0000_0001) begin
            $display("  PASS: 5 < 10 = true (unsigned)");
            pass_count = pass_count + 1;
        end else begin
            $display("  FAIL: Expected 00000001, Got %h", result);
            fail_count = fail_count + 1;
        end

        // ============================================
        // Test 13: Large addition
        // ============================================
        $display("Test 13: Large addition");
        test_count = test_count + 1;
        a = 32'h1234_5678;
        b = 32'h8765_4321;
        op = ADD;
        @(posedge clk);
        @(posedge clk);
        if (result === 32'h9999_9999) begin
            $display("  PASS: Large ADD = %h", result);
            pass_count = pass_count + 1;
        end else begin
            $display("  FAIL: Expected 99999999, Got %h", result);
            fail_count = fail_count + 1;
        end

        // ============================================
        // Test 14: Overflow detection
        // ============================================
        $display("Test 14: Overflow detection (signed)");
        test_count = test_count + 1;
        a = 32'h7FFF_FFFF;  // Max positive (signed)
        b = 32'h0000_0001;
        op = ADD;
        @(posedge clk);
        @(posedge clk);
        if (overflow === 1'b1) begin
            $display("  PASS: Overflow detected correctly");
            pass_count = pass_count + 1;
        end else begin
            $display("  FAIL: Overflow not detected, result=%h overflow=%b", result, overflow);
            fail_count = fail_count + 1;
        end

        // ============================================
        // Final Summary
        // ============================================
        @(posedge clk);
        @(posedge clk);
        $display("");
        $display("============================================");
        $display("TEST SUMMARY: %0d tests, %0d passed, %0d failed", test_count, pass_count, fail_count);
        $display("============================================");

        if (fail_count === 0) begin
            $display("ALL_TESTS_PASSED");
        end else begin
            $display("SOME_TESTS_FAILED");
        end

        #100;
        $finish;
    end

endmodule
