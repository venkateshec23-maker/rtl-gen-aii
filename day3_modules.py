# day3_modules.py
import rtl_utils

print("Power of 2 checks:")
print(f"8 is power of 2: {rtl_utils.is_power_of_two(8)}")
print(f"12 is power of 2: {rtl_utils.is_power_of_two(12)}")

from rtl_utils import generate_port_list, estimate_gates

adder_ports = [
    {"direction": "input", "name": "a", "width": 8},
    {"direction": "input", "name": "b", "width": 8},
    {"direction": "output", "name": "sum", "width": 8},
    {"direction": "output", "name": "carry"}
]

print("\nAdder ports:")
ports = generate_port_list(adder_ports)
for port in ports:
    print(f"  {port}")

gate_count = estimate_gates(8, "adder")
print(f"\nEstimated gates: {gate_count}")

import rtl_utils as ru

components = ru.get_supported_components()
print(f"\nSupported components: {components}")

test_cases = ru.suggest_test_cases(8, "adder")
print(f"Suggested test cases: {test_cases}")

def create_adder_design(bit_width):
    if not ru.is_power_of_two(bit_width):
        print(f"Warning: {bit_width} not power of 2")
    
    ports = [
        {"direction": "input", "name": "a", "width": bit_width},
        {"direction": "input", "name": "b", "width": bit_width},
        {"direction": "output", "name": "sum", "width": bit_width},
        {"direction": "output", "name": "carry"}
    ]
    
    module_name = f"adder_{bit_width}bit"
    code_lines = []
    
    code_lines.append(ru.add_comment(f"{bit_width}-bit Adder"))
    code_lines.append(f"module {module_name}(")
    code_lines.extend(ru.generate_port_list(ports))
    code_lines.append(");")
    code_lines.append("")
    code_lines.append(f"    // {bit_width}-bit addition")
    code_lines.append("    assign {carry, sum} = a + b;")
    code_lines.append("")
    code_lines.append("endmodule")
    
    code = ru.format_verilog_code(code_lines)
    
    return code, ru.estimate_gates(bit_width, "adder")

code, gates = create_adder_design(16)
print(f"\nGenerated Code ({gates} estimated gates):")
print(code)
