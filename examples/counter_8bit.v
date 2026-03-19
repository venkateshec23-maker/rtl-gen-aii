//==============================================================================
// Module: counter_8bit
// Description: 8-bit counter with synchronous reset and enable
// Author: RTL-Gen AI
//==============================================================================

module counter_8bit(
    input        clk,      // Clock input
    input        reset,    // Synchronous reset (active high)
    input        enable,   // Count enable
    output reg [7:0] count // Counter output
);

    always @(posedge clk) begin
        if (reset)
            count <= 8'd0;
        else if (enable)
            count <= count + 1;
    end

endmodule
