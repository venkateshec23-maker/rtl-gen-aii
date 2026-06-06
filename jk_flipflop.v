module jk_flipflop (
    input clk,
    input reset_n,
    input j,
    input k,
    output reg q,
    output q_bar
);
    assign q_bar = ~q;

    always @(posedge clk or negedge reset_n) begin
        if (!reset_n) begin
            q <= 1'b0;
        end else begin
            case ({j, k})
                2'b00: q <= q;       // Hold
                2'b01: q <= 1'b0;    // Reset
                2'b10: q <= 1'b1;    // Set
                2'b11: q <= ~q;      // Toggle
            endcase
        end
    end
endmodule
