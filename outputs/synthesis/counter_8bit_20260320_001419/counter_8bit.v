module counter_8bit(
    input        clk,
    input        reset,
    input        enable,
    output reg [7:0] count
);
    always @(posedge clk) begin
        if (reset)
            count <= 8'b0;
        else if (enable)
            count <= count + 1;
    end
endmodule