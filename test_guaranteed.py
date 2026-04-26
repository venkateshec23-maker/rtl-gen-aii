from guaranteed_flow import generate_guaranteed_gds

# Test 2: Custom RTL
print('=== TEST 2: Custom RTL ===')
custom_rtl = '''
module my_gate (input clk, reset_n, a, b, output reg y);
always @(posedge clk) begin
    if (!reset_n) y <= 0;
    else y <= a & b;
end
endmodule
'''
result = generate_guaranteed_gds(description='AND gate', module_name='my_gate', custom_rtl=custom_rtl)
print('Status:', result['status'])
print('GDS KB:', result['gds_size_kb'])
print('Method:', result['method_used'])
print()

# Test 3: Bad description (fallback)
print('=== TEST 3: Bad description ===')
result = generate_guaranteed_gds(description='asdfghjkl random nonsense', module_name='bad_desc')
print('Status:', result['status'])
print('GDS KB:', result['gds_size_kb'])
print('Method:', result['method_used'])
print()

# Test 4: Complex design
print('=== TEST 4: Complex design ===')
result = generate_guaranteed_gds(description='UART transmitter state machine 8N1', module_name='uart_tx')
print('Status:', result['status'])
print('GDS KB:', result['gds_size_kb'])
print('Method:', result['method_used'])
