// {{module_name}}.v
// Bit width: {{bit_width}}

module {{module_name}}(
    input [{{bit_width_minus_1}}:0] a,
    input [{{bit_width_minus_1}}:0] b,
    output [{{bit_width_minus_1}}:0] sum
);
    assign sum = a + b;
endmodule
