module alu_32bit (
    input  wire        clk,
    input  wire        rst_n,
    input  wire [31:0] a,
    input  wire [31:0] b,
    input  wire [3:0]  op,
    output reg  [31:0] result,
    output reg         zero,
    output reg         carry,
    output reg         overflow
);

    // Operation codes
    localparam ADD  = 4'b0000;
    localparam SUB  = 4'b0001;
    localparam AND  = 4'b0010;
    localparam OR   = 4'b0011;
    localparam XOR  = 4'b0100;
    localparam NOT  = 4'b0101;
    localparam SLL  = 4'b0110;  // Shift left logical
    localparam SRL  = 4'b0111;  // Shift right logical
    localparam SLT  = 4'b1000;  // Set less than (signed)
    localparam SLTU = 4'b1001;  // Set less than unsigned

    reg [32:0] temp_result;
    wire signed [31:0] a_signed = a;
    wire signed [31:0] b_signed = b;

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            result   <= 32'b0;
            zero     <= 1'b0;
            carry    <= 1'b0;
            overflow <= 1'b0;
        end
        else begin
            case (op)
                ADD: begin
                    temp_result = {1'b0, a} + {1'b0, b};
                    result   <= temp_result[31:0];
                    carry    <= temp_result[32];
                    overflow <= (a[31] == b[31]) && (result[31] != a[31]);
                    zero     <= (temp_result[31:0] == 32'b0);
                end

                SUB: begin
                    temp_result = {1'b0, a} - {1'b0, b};
                    result   <= temp_result[31:0];
                    carry    <= temp_result[32];
                    overflow <= (a[31] != b[31]) && (result[31] != a[31]);
                    zero     <= (temp_result[31:0] == 32'b0);
                end

                AND: begin
                    result   <= a & b;
                    zero     <= ((a & b) == 32'b0);
                    carry    <= 1'b0;
                    overflow <= 1'b0;
                end

                OR: begin
                    result   <= a | b;
                    zero     <= ((a | b) == 32'b0);
                    carry    <= 1'b0;
                    overflow <= 1'b0;
                end

                XOR: begin
                    result   <= a ^ b;
                    zero     <= ((a ^ b) == 32'b0);
                    carry    <= 1'b0;
                    overflow <= 1'b0;
                end

                NOT: begin
                    result   <= ~a;
                    zero     <= ((~a) == 32'b0);
                    carry    <= 1'b0;
                    overflow <= 1'b0;
                end

                SLL: begin
                    result   <= a << b[4:0];
                    zero     <= ((a << b[4:0]) == 32'b0);
                    carry    <= 1'b0;
                    overflow <= 1'b0;
                end

                SRL: begin
                    result   <= a >> b[4:0];
                    zero     <= ((a >> b[4:0]) == 32'b0);
                    carry    <= 1'b0;
                    overflow <= 1'b0;
                end

                SLT: begin
                    result   <= (a_signed < b_signed) ? 32'd1 : 32'd0;
                    zero     <= (a_signed >= b_signed);
                    carry    <= 1'b0;
                    overflow <= 1'b0;
                end

                SLTU: begin
                    result   <= (a < b) ? 32'd1 : 32'd0;
                    zero     <= (a >= b);
                    carry    <= 1'b0;
                    overflow <= 1'b0;
                end

                default: begin
                    result   <= 32'b0;
                    zero     <= 1'b0;
                    carry    <= 1'b0;
                    overflow <= 1'b0;
                end
            endcase
        end
    end

endmodule
