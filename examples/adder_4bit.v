//==============================================================================
// Module: adder_4bit
// Description: 4-bit binary adder with carry
// Author: RTL-Gen AI
// Date: 2026-02-20
//==============================================================================

module adder_4bit(
    input  [3:0] a,      // First operand
    input  [3:0] b,      // Second operand
    input        cin,    // Carry input
    output [3:0] sum,    // Sum output
    output       cout    // Carry output
);

    // Concatenate carry out and sum
    assign {cout, sum} = a + b + cin;

endmodule
