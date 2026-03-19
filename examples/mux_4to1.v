//==============================================================================
// Module: mux_4to1
// Description: 4-to-1 multiplexer with 8-bit data width
// Author: RTL-Gen AI
//==============================================================================

module mux_4to1(
    input  [7:0] in0,    // Input 0
    input  [7:0] in1,    // Input 1
    input  [7:0] in2,    // Input 2
    input  [7:0] in3,    // Input 3
    input  [1:0] sel,    // Select signal
    output reg [7:0] out // Output
);

    always @(*) begin
        case (sel)
            2'b00: out = in0;
            2'b01: out = in1;
            2'b10: out = in2;
            2'b11: out = in3;
            default: out = 8'h00;
        endcase
    end

endmodule
