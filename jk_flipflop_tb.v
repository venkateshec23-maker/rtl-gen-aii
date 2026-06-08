`timescale 1ns/1ps
module jk_flipflop_tb();
    reg clk;
    reg reset_n;
    reg j;
    reg k;
    wire q;
    wire q_bar;
    integer pass_count = 0;
    integer fail_count = 0;
    integer test_num = 0;
    integer i;
    reg expected_q;

    jk_flipflop dut(.clk(clk), .reset_n(reset_n), .j(j), .k(k), .q(q), .q_bar(q_bar));

    initial clk = 0;
    always #5 clk = ~clk;

    task check_jk;
        input vj, vk;
        input exp_q;
        begin
            j = vj; k = vk;
            @(posedge clk); #1;
            test_num = test_num + 1;
            if (q === exp_q) begin
                $display("PASS Test %0d: j=%b k=%b q=%b expected=%b", test_num, vj, vk, q, exp_q);
                pass_count = pass_count + 1;
            end else begin
                $display("FAIL Test %0d: j=%b k=%b q=%b expected=%b", test_num, vj, vk, q, exp_q);
                fail_count = fail_count + 1;
            end
        end
    endtask

    initial begin
        $dumpfile("trace.vcd");
        $dumpvars(0, jk_flipflop_tb);

        // Initialize and apply reset
        reset_n = 1'b0;
        j = 0; k = 0;
        repeat(3) @(posedge clk); #1;

        // Tests 1-5: Reset verification — q should be 0 after reset
        for (i = 0; i < 5; i = i + 1) begin
            @(posedge clk); #1;
            test_num = test_num + 1;
            if (q === 1'b0) begin
                $display("PASS Test %0d: reset q=%b (expected 0)", test_num, q);
                pass_count = pass_count + 1;
            end else begin
                $display("FAIL Test %0d: reset q=%b (expected 0)", test_num, q);
                fail_count = fail_count + 1;
            end
        end

        // Release reset
        reset_n = 1'b1;
        @(posedge clk); #1;
        expected_q = 0;  // After reset, q=0

        // Tests 6-25: HOLD mode (j=0, k=0) — q should NOT change (20 tests)
        j = 0; k = 0;
        for (i = 0; i < 20; i = i + 1) begin
            check_jk(0, 0, expected_q);
            // expected_q stays the same
        end

        // Tests 26-45: SET mode (j=1, k=0) — q should become 1 (20 tests)
        // After first SET, q=1 and remains 1 for all subsequent SETs
        for (i = 0; i < 20; i = i + 1) begin
            expected_q = 1;  // SET always drives q=1
            check_jk(1, 0, expected_q);
        end

        // Tests 46-65: RESET mode (j=0, k=1) — q should become 0 (20 tests)
        // After first RESET, q=0 and remains 0 for all subsequent RESETs
        for (i = 0; i < 20; i = i + 1) begin
            expected_q = 0;  // RESET always drives q=0
            check_jk(0, 1, expected_q);
        end

        // Tests 66-85: TOGGLE mode (j=1, k=1) — q should flip each clock (20 tests)
        // Starting from q=0 (after RESET mode above)
        expected_q = 0;
        for (i = 0; i < 20; i = i + 1) begin
            expected_q = ~expected_q;  // TOGGLE flips q
            check_jk(1, 1, expected_q);
        end

        // Tests 86-90: q_bar complementarity check (5 tests)
        // SET mode: q=1, q_bar should be 0
        for (i = 0; i < 5; i = i + 1) begin
            j = 1; k = 0;
            @(posedge clk); #1;
            expected_q = 1;
            test_num = test_num + 1;
            if (q === 1'b1 && q_bar === 1'b0) begin
                $display("PASS Test %0d: SET q=%b q_bar=%b", test_num, q, q_bar);
                pass_count = pass_count + 1;
            end else begin
                $display("FAIL Test %0d: SET q=%b q_bar=%b", test_num, q, q_bar);
                fail_count = fail_count + 1;
            end
        end

        // Tests 91-95: q_bar complementarity in RESET mode (5 tests)
        for (i = 0; i < 5; i = i + 1) begin
            j = 0; k = 1;
            @(posedge clk); #1;
            expected_q = 0;
            test_num = test_num + 1;
            if (q === 1'b0 && q_bar === 1'b1) begin
                $display("PASS Test %0d: RESET q=%b q_bar=%b", test_num, q, q_bar);
                pass_count = pass_count + 1;
            end else begin
                $display("FAIL Test %0d: RESET q=%b q_bar=%b", test_num, q, q_bar);
                fail_count = fail_count + 1;
            end
        end

        // Tests 96-98: Reset-in-middle recovery (3 tests)
        // First toggle to q=1
        j = 1; k = 0; @(posedge clk); #1;
        // Now assert reset
        reset_n = 1'b0;
        @(posedge clk); #1;
        test_num = test_num + 1;
        if (q === 1'b0) begin
            $display("PASS Test %0d: mid-reset q=%b", test_num, q);
            pass_count = pass_count + 1;
        end else begin
            $display("FAIL Test %0d: mid-reset q=%b (expected 0)", test_num, q);
            fail_count = fail_count + 1;
        end

        // Release reset — clear inputs first to avoid immediate SET
        j = 0; k = 0;
        reset_n = 1'b1;
        @(posedge clk); #1;
        test_num = test_num + 1;
        if (q === 1'b0) begin
            $display("PASS Test %0d: post-reset q=%b", test_num, q);
            pass_count = pass_count + 1;
        end else begin
            $display("FAIL Test %0d: post-reset q=%b (expected 0)", test_num, q);
            fail_count = fail_count + 1;
        end

        // Test 98: SET after reset recovery
        j = 1; k = 0; @(posedge clk); #1;
        test_num = test_num + 1;
        if (q === 1'b1) begin
            $display("PASS Test %0d: recovery SET q=%b", test_num, q);
            pass_count = pass_count + 1;
        end else begin
            $display("FAIL Test %0d: recovery SET q=%b (expected 1)", test_num, q);
            fail_count = fail_count + 1;
        end

        // Tests 99-100: Final mode transitions
        // RESET after SET
        j = 0; k = 1; @(posedge clk); #1;
        test_num = test_num + 1;
        if (q === 1'b0) begin
            $display("PASS Test %0d: SET->RESET q=%b", test_num, q);
            pass_count = pass_count + 1;
        end else begin
            $display("FAIL Test %0d: SET->RESET q=%b (expected 0)", test_num, q);
            fail_count = fail_count + 1;
        end

        // TOGGLE from 0
        j = 1; k = 1; @(posedge clk); #1;
        test_num = test_num + 1;
        if (q === 1'b1) begin
            $display("PASS Test %0d: TOGGLE from 0 q=%b", test_num, q);
            pass_count = pass_count + 1;
        end else begin
            $display("FAIL Test %0d: TOGGLE from 0 q=%b (expected 1)", test_num, q);
            fail_count = fail_count + 1;
        end

        $display("RESULTS: %0d PASS / %0d FAIL", pass_count, fail_count);
        if (fail_count == 0) $display("ALL_TESTS_PASSED");
        else $display("TESTS_FAILED");
        $finish;
    end
endmodule
