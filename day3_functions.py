# day3_functions.py

def greet():
    """This is a docstring - describes what function does"""
    print("Hello from a function!")

greet()

def generate_module_name(component_type, bit_width):
    module_name = f"{component_type}_{bit_width}bit"
    return module_name

print(generate_module_name("adder", 8))
print(generate_module_name("counter", 16))

def create_port_declaration(direction, name, bit_width=1):
    if bit_width == 1:
        return f"    {direction} {name}"
    else:
        return f"    {direction} [{bit_width-1}:0] {name}"

print(create_port_declaration("input", "clk"))
print(create_port_declaration("input", "data", 8))
print(create_port_declaration("output", "result", 16))

def create_design_spec(name, bit_width=8, design_type="combinational"):
    spec = {
        "name": name,
        "bit_width": bit_width,
        "type": design_type,
        "created": "2026-03-18"
    }
    return spec

print(create_design_spec("adder", 16, "combinational"))
print(create_design_spec("counter"))

def analyze_design(description):
    desc = description.lower()
    component = "unknown"
    width = 8
    has_clock = "clock" in desc or "clk" in desc
    
    if "adder" in desc:
        component = "adder"
    elif "counter" in desc:
        component = "counter"
    elif "alu" in desc:
        component = "alu"
    
    for w in [64, 32, 16, 8, 4]:
        if f"{w}-bit" in desc or f"{w} bit" in desc:
            width = w
            break
            
    return component, width, has_clock

comp, width, clock = analyze_design("Create a 16-bit adder with clock")
print(f"\nAnalysis: {comp}, {width}bit, clock={clock}")

def validate_bit_width(width):
    if not isinstance(width, int):
        return False, "Bit width must be integer"
    if width < 1:
        return False, "Bit width must be positive"
    if width > 64:
        return False, "Bit width too large (max 64)"
    if (width & (width - 1)) != 0:
        return False, "Bit width must be power of 2"
    return True, "Valid bit width"

# COMPOSITION
def extract_bit_width(description):
    desc = description.lower()
    for width in [64, 32, 16, 8, 4]:
        if f"{width}-bit" in desc or f"{width} bit" in desc:
            return width
    return 8

def extract_component(description):
    desc = description.lower()
    components = {
        "adder": ["adder", "add"],
        "counter": ["counter", "count"],
        "alu": ["alu", "arithmetic"],
        "multiplexer": ["mux", "multiplexer"]
    }
    
    for comp, keywords in components.items():
        for keyword in keywords:
            if keyword in desc:
                return comp
    return "unknown"

def extract_operations(description):
    desc = description.lower()
    ops = []
    all_ops = ["add", "sub", "and", "or", "xor", "not"]
    for op in all_ops:
        if op in desc:
            ops.append(op.upper())
    return ops

def parse_design_request(description):
    warnings_list = []
    
    comp = extract_component(description)
    ops = extract_operations(description)
    
    if comp == "unknown":
        warnings_list.append("Could not identify component type")
    if comp == "alu" and not ops:
        warnings_list.append("ALU specified but no operations found")
        
    result = {
        "original": description,
        "bit_width": extract_bit_width(description),
        "component": comp,
        "operations": ops,
        "has_clock": "clock" in description.lower() or "clk" in description.lower(),
        "is_valid": len(warnings_list) == 0,
        "warnings": warnings_list
    }
    
    return result

test_descriptions = [
    "Create an 8-bit adder",
    "Design a 16-bit counter with clock and reset",
    "Build a 32-bit ALU with ADD, SUB, AND operations"
]

print("\n" + "="*50)
print("Design Request Parser")
print("="*50)

for desc in test_descriptions:
    print(f"\nInput: {desc}")
    result = parse_design_request(desc)
    print(f"Parsed: {result['component']} ({result['bit_width']}bit)")
    ops = result['operations']
    if isinstance(ops, list) and ops:
        print(f"Ops: {', '.join(ops)}")
    if result['warnings']:
        print(f"Warnings: {result['warnings']}")
