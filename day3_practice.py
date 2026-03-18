# day3_practice.py

# EXERCISE 1
def generate_module_name(comp_type, width, suffix="rtl"):
    return f"{comp_type}_{width}bit_{suffix}"

print(generate_module_name("adder", 8))
print(generate_module_name("counter", 16, "tb"))

# EXERCISE 2
valid_components = ["adder", "counter", "alu", "mux"]

def validate_design_input(description):
    if not description:
        return False, "Empty input"
    if len(description) < 10:
        return False, "Input too short"
    
    desc_lower = description.lower()
    has_comp = False
    for comp in valid_components:
        if comp in desc_lower:
            has_comp = True
            break
            
    if not has_comp:
        return False, "No component type"
        
    return True, "Valid"

print(validate_design_input(""))
print(validate_design_input("8-bit"))
print(validate_design_input("Create an 8-bit adder"))

# EXERCISE 3
def count_ports(verilog_code):
    count = 0
    for line in verilog_code.split('\n'):
        line = line.strip()
        if line.startswith("input") or line.startswith("output"):
            count += 1
    return count

code = """
module test(
    input clk,
    input rst,
    output [7:0] data
);
endmodule
"""
print(f"Port count: {count_ports(code)}")

# EXERCISE 4
def estimate_area(bit_width, comp_type):
    if comp_type == "adder":
        return bit_width * 100
    elif comp_type == "counter":
        return bit_width * 150
    elif comp_type == "alu":
        return bit_width * 300
    else:
        return bit_width * 200

def estimate_power(area, frequency_mhz):
    return area * frequency_mhz * 0.001

area = estimate_area(16, "adder")
power = estimate_power(area, 100)
print(f"16-bit adder: area={area}, power={power:.2f}mW")

# EXERCISE 5
import verilog_helpers as vh

comment = vh.add_comment("This is a test")
indented = vh.indent_line("$display('hello');")
always = vh.create_always_block("@(posedge clk)", ["q <= d;"])

print("\nHelper Outputs:")
print(comment)
print(indented)
print(always)
