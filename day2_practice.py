# day2_practice.py

# EXERCISE 1
bit_width = 24
complexity = ""

if bit_width <= 8:
    complexity = "Simple"
elif bit_width <= 16:
    complexity = "Medium"
elif bit_width <= 32:
    complexity = "Complex"
else:
    complexity = "Very Complex"

print(f"Design with {bit_width} bits is: {complexity}")

# EXERCISE 2
port_names = []
for i in range(8):
    port_names.append(f"a{i}")

print(f"Ports: {port_names}")

# EXERCISE 3
design = {
    "name": "my_adder",
    "bit_width": 8,
}
required_fields = ["name", "bit_width", "type", "ports"]
missing_fields = []

for field in required_fields:
    if field not in design:
        missing_fields.append(field)

if missing_fields:
    print(f"Missing fields: {missing_fields}")
else:
    print("Design spec is complete!")

# EXERCISE 4
description = "This design should add and subtract, and also do AND operations"
operations = ["add", "sub", "and", "or", "xor"]
found_ops = []

desc_lower = description.lower()
for op in operations:
    if op in desc_lower:
        found_ops.append(op)

print(f"Found operations: {found_ops}")
print(f"Total count: {len(found_ops)}")

# EXERCISE 5
print("\nTest vectors for 2-bit adder:")
print("a\tb\tsum\tcarry")

for a in range(4):
    for b in range(4):
        sum_val = a + b
        carry = 1 if sum_val > 3 else 0
        sum_4bit = sum_val & 3
        print(f"{a}\t{b}\t{sum_4bit}\t{carry}")
