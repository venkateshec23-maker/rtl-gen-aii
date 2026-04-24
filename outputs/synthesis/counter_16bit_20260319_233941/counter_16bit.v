
module counter_16bit(
    input clk, rst, en,
    output reg [15:0] count
);
    always @(posedge clk or posedge rst)
        if (rst) count <= 0;
        else if (en) count <= count + 1;
endmodule
