module counter_4bit (
    input clk, reset, enable,
    output reg [3:0] count
);
    always @(posedge clk) begin
        if (reset)
            count <= 4'b0000;
        else if (enable)
            count <= count + 1'b1;
    end
endmodule