module alu_8bit(
    input  [7:0] a, b,
    input  [1:0] op,
    output reg [7:0] result,
    output reg       zero
);
    localparam ADD = 2'b00, SUB = 2'b01, AND_OP = 2'b10, OR_OP = 2'b11;

    always @(*) begin
        case(op)
            ADD:    result = a + b;
            SUB:    result = a - b;
            AND_OP: result = a & b;
            OR_OP:  result = a | b;
            default: result = 8'b0;
        endcase
        zero = (result == 8'b0);
    end
endmodule