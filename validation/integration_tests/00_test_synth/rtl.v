module adder_8bit(
    input  clk,
    input  [7:0] a,
    input  [7:0] b,
    output reg [8:0] sum
);

always @(posedge clk) begin
    sum <= a + b;
end

endmodule
