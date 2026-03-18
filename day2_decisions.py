# day2_decisions.py

bit_width = 16

if bit_width > 8:
    print("This is a wide design")
    print("Will use more resources")

if bit_width <= 8:
    print("Small design - easy to verify")
else:
    print("Large design - complex verification needed")

if bit_width <= 4:
    complexity = "Simple"
    area = "Small"
elif bit_width <= 16:
    complexity = "Medium"
    area = "Medium"
elif bit_width <= 32:
    complexity = "Complex"
    area = "Large"
else:
    complexity = "Very Complex"
    area = "Very Large"

print(f"\nDesign complexity: {complexity}")
print(f"Area estimate: {area}")

# logical operators
is_combinational = True
has_clock = False
bit_width = 8

if is_combinational and has_clock:
    print("This is sequential (has clock)")
elif is_combinational and not has_clock:
    print("This is pure combinational")

if is_combinational or has_clock:
    print("Design has either combinational logic or clock")

if not has_clock:
    print("No clock signal needed")

def check_design_rules(bit_width, has_clock, operation_count):
    issues = []
    if bit_width not in [1, 2, 4, 8, 16, 32, 64]:
        issues.append(f"Bit width {bit_width} not standard")
    if has_clock and operation_count < 2:
        issues.append("Clocked design needs at least 2 operations")
    if bit_width > 32 and operation_count > 10:
        issues.append("Large design with many ops - may be complex")
    if bit_width < 1 or operation_count < 0:
        issues.append("Invalid negative values")
    passes = len(issues) == 0
    return passes, issues

test_cases = [
    (8, False, 4),
    (16, True, 1),
    (12, False, 5),
]

for width, clock, ops in test_cases:
    print(f"\nTesting: {width}-bit, clock={clock}, ops={ops}")
    passes, issues = check_design_rules(width, clock, ops)
    if passes:
        print("✓ Design passes all checks")
    else:
        print("✗ Issues found:")
        for issue in issues:
            print(f"  - {issue}")

operations = ["ADD", "SUB", "MUL", "DIV"]
for op in operations:
    print(f"  - Processing {op}")

for width in range(4, 17, 4):
    print(f"  Generating {width}-bit design")

port_names = ["clk", "rst", "data_in", "data_out"]
for i, port in enumerate(port_names):
    print(f"  Port {i}: {port}")

sim_time = 0
end_time = 100
time_step = 10
while sim_time <= end_time:
    print(f"  Time: {sim_time} ns")
    sim_time += time_step

for op in operations:
    if op == "MUL":
        print(f"  Found {op}! Stopping search.")
        break
    print(f"  Checking {op}...")

for i in range(10):
    if i % 2 != 0:
        continue
    print(f"  {i} is even")

def generate_port_list(prefix, count, bit_width, direction="input"):
    ports = []
    for i in range(count):
        if bit_width > 1:
            port = f"{direction} [{bit_width-1}:0] {prefix}{i}"
        else:
            port = f"{direction} {prefix}{i}"
        ports.append(port)
    return ports

data_ports = generate_port_list("data", 4, 8, "input")
for port in data_ports:
    print(f"  {port}")

addr_ports = generate_port_list("addr", 2, 16, "output")
for port in addr_ports:
    print(f"  {port}")

ops = ["ADD", "SUB", "AND", "OR"]
for i, op1 in enumerate(ops):
    for j, op2 in enumerate(ops):
        if i < j:
            print(f"  {op1} + {op2}")
