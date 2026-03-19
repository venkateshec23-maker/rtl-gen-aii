//==============================================================================
// Testbench: adder_4bit_tb
// Description: Testbench for 4-bit adder
//==============================================================================

`timescale 1ns/1ps

module adder_4bit_tb;
    reg  [3:0] a;
    reg  [3:0] b;
    reg        cin;
    wire [3:0] sum;
    wire       cout;
    
    integer tests_passed = 0;
    integer tests_failed = 0;
    
    // Instantiate DUT
    adder_4bit dut (
        .a(a),
        .b(b),
        .cin(cin),
        .sum(sum),
        .cout(cout)
    );
    
    // Test cases
    initial begin
        $dumpfile("adder_4bit.vcd");
        $dumpvars(0, adder_4bit_tb);
        
        // Test 1: 0 + 0 + 0 = 0
        a = 4'b0000; b = 4'b0000; cin = 0; #10;
        if (sum == 4'b0000 && cout == 0) begin
            $display("✓ Test 1 PASSED: 0 + 0 + 0 = %d (carry=%b)", sum, cout);
            tests_passed = tests_passed + 1;
        end else begin
            $display("✗ Test 1 FAILED");
            tests_failed = tests_failed + 1;
        end
        
        // Test 2: 5 + 3 + 0 = 8
        a = 4'b0101; b = 4'b0011; cin = 0; #10;
        if (sum == 4'b1000 && cout == 0) begin
            $display("✓ Test 2 PASSED: 5 + 3 + 0 = %d (carry=%b)", sum, cout);
            tests_passed = tests_passed + 1;
        end else begin
            $display("✗ Test 2 FAILED");
            tests_failed = tests_failed + 1;
        end
        
        // Test 3: 15 + 1 + 0 = 16 (overflow)
        a = 4'b1111; b = 4'b0001; cin = 0; #10;
        if (sum == 4'b0000 && cout == 1) begin
            $display("✓ Test 3 PASSED: 15 + 1 + 0 = %d (carry=%b)", sum, cout);
            tests_passed = tests_passed + 1;
        end else begin
            $display("✗ Test 3 FAILED");
            tests_failed = tests_failed + 1;
        end
        
        // Test 4: 7 + 8 + 1 = 16
        a = 4'b0111; b = 4'b1000; cin = 1; #10;
        if (sum == 4'b0000 && cout == 1) begin
            $display("✓ Test 4 PASSED: 7 + 8 + 1 = %d (carry=%b)", sum, cout);
            tests_passed = tests_passed + 1;
        end else begin
            $display("✗ Test 4 FAILED");
            tests_failed = tests_failed + 1;
        end
        
        // Summary
        $display("\n========================================");
        $display("Test Summary:");
        $display("  Passed: %d", tests_passed);
        $display("  Failed: %d", tests_failed);
        if (tests_failed == 0)
            $display("  Status: ALL TESTS PASSED ✓");
        else
            $display("  Status: SOME TESTS FAILED ✗");
        $display("========================================");
        
        $finish;
    end
endmodule
