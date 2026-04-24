
module alu_8bit (
    input [7:0] operand_a,
    input [7:0] operand_b,
    input [3:0] opcode,
    input enable,
    output reg [7:0] result,
    output reg zero_flag,
    output reg carry_flag,
    output reg overflow_flag
);

    localparam ADD = 4'b0000;
    localparam SUB = 4'b0001;
    localparam AND = 4'b0010;
    localparam OR  = 4'b0011;
    localparam XOR = 4'b0100;
    localparam SHL = 4'b0101;
    localparam SHR = 4'b0110;
    localparam CMP = 4'b0111;

    wire [8:0] temp_result;
    
    always @(*) begin
        if (!enable) begin
            result = 8'b0;
            zero_flag = 1'b0;
            carry_flag = 1'b0;
            overflow_flag = 1'b0;
        end
        else begin
            case (opcode)
                ADD: begin
                    {carry_flag, result} = operand_a + operand_b;
                    overflow_flag = (operand_a[7] == operand_b[7]) && (operand_a[7] != result[7]);
                    zero_flag = (result == 8'b0);
                end
                SUB: begin
                    {carry_flag, result} = operand_a - operand_b;
                    overflow_flag = (operand_a[7] != operand_b[7]) && (operand_a[7] != result[7]);
                    zero_flag = (result == 8'b0);
                end
                AND: begin
                    result = operand_a & operand_b;
                    zero_flag = (result == 8'b0);
                    carry_flag = 1'b0;
                    overflow_flag = 1'b0;
                end
                OR: begin
                    result = operand_a | operand_b;
                    zero_flag = (result == 8'b0);
                    carry_flag = 1'b0;
                    overflow_flag = 1'b0;
                end
                XOR: begin
                    result = operand_a ^ operand_b;
                    zero_flag = (result == 8'b0);
                    carry_flag = 1'b0;
                    overflow_flag = 1'b0;
                end
                SHL: begin
                    {carry_flag, result} = {operand_a, 1'b0};
                    zero_flag = (result == 8'b0);
                    overflow_flag = 1'b0;
                end
                SHR: begin
                    result = operand_a >> operand_b[2:0];
                    carry_flag = operand_a[0];
                    zero_flag = (result == 8'b0);
                    overflow_flag = 1'b0;
                end
                CMP: begin
                    {carry_flag, result} = operand_a - operand_b;
                    overflow_flag = (operand_a[7] != operand_b[7]) && (operand_a[7] != result[7]);
                    zero_flag = (result == 8'b0);
                end
                default: begin
                    result = 8'b0;
                    zero_flag = 1'b0;
                    carry_flag = 1'b0;
                    overflow_flag = 1'b0;
                end
            endcase
        end
    end
endmodule
