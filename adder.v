
module adder_8bit (
    input  clk,
    input  reset_n,
    input  [7:0] a, b,
    output reg [8:0] sum
);
  always @(posedge clk) begin
    if (!reset_n) sum <= 9'b0;
    else          sum <= a + b;
  end
endmodule
