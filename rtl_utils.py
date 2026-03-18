"""
RTL Generation Utility Functions
This module contains helper functions for RTL code generation
"""

def is_power_of_two(n):
    if n <= 0:
        return False
    return (n & (n - 1)) == 0

def validate_component_type(comp_type):
    supported = ["adder", "counter", "alu", "multiplexer", "register"]
    return comp_type.lower() in supported

def get_supported_components():
    return ["adder", "counter", "alu", "multiplexer", "register"]

def generate_module_header(module_name):
    return f"module {module_name}("

def generate_module_footer():
    return "endmodule"

def generate_port_list(ports_config):
    ports = []
    for i, port in enumerate(ports_config):
        direction = port['direction']
        name = port['name']
        width = port.get('width', 1)
        
        if width > 1:
            decl = f"    {direction} [{width-1}:0] {name}"
        else:
            decl = f"    {direction} {name}"
            
        if i < len(ports_config) - 1:
            decl += ","
        ports.append(decl)
    return ports

def estimate_gates(bit_width, component_type):
    base_counts = {
        "adder": bit_width * 5,
        "counter": bit_width * 4,
        "alu": bit_width * 10,
        "multiplexer": bit_width * 2,
        "register": bit_width * 6
    }
    return base_counts.get(component_type, bit_width * 3)

def suggest_test_cases(bit_width, component_type):
    if component_type == "adder":
        return min(100, 2 ** (bit_width * 2))
    elif component_type == "counter":
        return min(50, 2 ** bit_width)
    else:
        return min(20, 2 ** bit_width)

def format_verilog_code(code_lines):
    return "\n".join(code_lines)

def add_comment(comment):
    return f"// {comment}"

def create_filename(module_name):
    return f"{module_name}.v"
