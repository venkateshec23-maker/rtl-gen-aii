module my_counter (
    input clk,
    input reset,
    output [7:0] count
);
    reg [7:0] counter;
    always @(posedge clk)
        if (reset)
            counter <= 0;
        else
            counter <= counter + 1;
    assign count = counter;
endmodule