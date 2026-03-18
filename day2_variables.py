# day2_variables.py

# ============================================
# SIMPLE VARIABLES
# ============================================

# Integer (whole numbers)
bit_width = 8
port_count = 4
max_value = 255

print(f"Bit width: {bit_width}")
print(f"Port count: {port_count}")
print(f"Max value: {max_value}")

# Float (decimal numbers)
clock_frequency = 100.5  # MHz
voltage = 1.2  # Volts
probability = 0.95

print(f"\nClock: {clock_frequency} MHz")
print(f"Voltage: {voltage} V")

# String (text)
module_name = "adder_8bit"
description = "This is an 8-bit adder"
author = "RTL-Gen AII"

print(f"\nModule: {module_name}")
print(f"Description: {description}")

# Boolean (True/False)
is_verified = False
has_errors = True
is_synthesizable = True

print(f"\nVerified? {is_verified}")
print(f"Has errors? {has_errors}")

# ============================================
# NAMING RULES
# ============================================
clock_frequency_mhz = 100

# Quick Exercise: Variables for 8-bit counter
counter_width = 8
counter_name = "counter_8bit"
has_reset = True
print(f"\nCounter Name: {counter_name}, Width: {counter_width}, Reset: {has_reset}")

# ============================================
# NUMBERS (int, float)
# ============================================
port_count = 4
bit_depth = 16
register_count = 32

operating_freq = 100.5
power_consumption = 0.25
area_estimate = 1200.75

total_pins = port_count * bit_depth
print(f"Total pins needed: {total_pins}")

# ============================================
# STRINGS (str) - Text Data
# ============================================
module_name = "alu_32bit"
verilog_code = "assign sum = a + b;"
file_path = "./outputs/alu_32bit.v"

print(module_name.upper())
print(module_name.lower())
print(module_name.replace("32", "64"))
print("alu" in module_name)
print(module_name.startswith("alu"))
print(module_name.endswith(".v"))
print(f"Name length: {len(module_name)} characters")

# ============================================
# LISTS - Ordered Collections
# ============================================
operations = ["ADD", "SUB", "AND", "OR", "XOR"]
print(f"Operations: {operations}")
print(f"First operation: {operations[0]}")
print(f"Last operation: {operations[-1]}")
print(f"Number of operations: {len(operations)}")

operations.append("NOT")
print(f"After append: {operations}")

operations.remove("AND")
print(f"After remove: {operations}")

bit_widths = [8, 16, 32, 64]
print(f"Bit widths: {bit_widths}")

# ============================================
# DICTIONARIES - Key-Value Pairs
# ============================================
design_spec = {
    "name": "alu_32bit",
    "type": "combinational",
    "bit_width": 32,
    "operations": ["ADD", "SUB", "AND"],
    "verified": False
}

print(f"\nDesign name: {design_spec['name']}")
print(f"Type: {design_spec['type']}")
print(f"Bit width: {design_spec['bit_width']}")
print(f"Operations: {design_spec['operations']}")

design_spec["verified"] = True
design_spec["author"] = "RTL-Gen AII"
print(f"Updated spec: {design_spec}")

# ============================================
# TYPE CHECKING
# ============================================
print(f"\nType of bit_width: {type(bit_depth)}")
print(f"Type of module_name: {type(module_name)}")
print(f"Type of operations: {type(operations)}")
print(f"Type of design_spec: {type(design_spec)}")

# Quick Exercise: Design Specification
counter_spec = {
    "name": "counter_8bit",
    "type": "sequential",
    "has_reset": True,
    "max_count": 255
}
print(f"Counter Spec: {counter_spec}")
