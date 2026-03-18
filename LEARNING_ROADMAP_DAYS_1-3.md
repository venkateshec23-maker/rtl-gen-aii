# RTL-Gen AIII: Phase 1 Foundation - Learning Roadmap (Part 1/6)

## 3-Day Plan: Days 1-3

---

## DAY 1: Development Environment Setup

### 🎯 **Today's Goal**
Install all necessary software and verify everything works. By tonight, you'll have a fully functional development environment.

### ⏱️ **Time Allocation (4-5 hours)**
- Theory/Reading: 45 minutes
- Step-by-Step Setup: 2 hours
- Verification & Testing: 1 hour
- Troubleshooting: 30-45 minutes

---

### 📚 **Part 1: Understanding Your Tools (30 minutes)**

**Why This Matters**
Before installing anything, understand what each tool does:

| Tool | What It Is | Analogy |
|------|------------|---------|
| **Python** | Programming language | Like having a workshop with tools |
| **VS Code** | Code editor | Your workbench where you build things |
| **Git** | Version control | Like "Track Changes" in Word, but for code |
| **Terminal** | Command interface | Talking directly to your computer |

**Your Development Workflow Will Be:**
```
Write Code (VS Code) → Run Code (Python) → Track Changes (Git) → Save Progress
```

---

### 💻 **Part 2: Python Installation (45 minutes)**

#### **Windows Installation**
```bash
Step 1: Go to python.org/downloads
Step 2: Download Python 3.11 or 3.12
Step 3: RUN THE INSTALLER - CRITICAL: Check "Add Python to PATH"
Step 4: Click "Install Now"
Step 5: Wait for installation to complete
```

**What is PATH?** (Simple Explanation)
PATH is your computer's address book. When you type `python`, your computer checks PATH to find where Python lives. Without it, your computer says "I don't know what 'python' means!"

#### **Mac Installation**
```bash
# Option 1: Download from python.org (easier for beginners)
# Option 2: Using Homebrew (if you have it)
brew install python@3.11
```

#### **Linux Installation (Ubuntu/Debian)**
```bash
sudo apt update
sudo apt install python3 python3-pip
```

#### **Verification (Do This Immediately!)**
Open Terminal/Command Prompt and type:
```bash
python --version
# Should show: Python 3.11.x or higher

pip --version
# Should show: pip 23.x.x
```

**Expected Output Examples:**
```
✓ Good: Python 3.11.5
✗ Bad: 'python' is not recognized...
```

---

### 📝 **Part 3: VS Code Setup (30 minutes)**

#### **Installation Steps**
1. Visit code.visualstudio.com
2. Download for your OS
3. Run installer (default options are fine)

#### **Essential Extensions (Install ALL)**
Open VS Code → Click Extensions icon (or Ctrl+Shift+X)

```python
# MUST INSTALL:
1. "Python" by Microsoft
   - Why: Adds Python language support, debugging
   
2. "Pylance" by Microsoft  
   - Why: Smart code completion, error checking
   
3. "Code Runner" by Jun Han
   - Why: Run code with one click
   
4. "GitLens" by GitKraken
   - Why: See who changed what, when
```

**After Installing:** Restart VS Code

---

### 🎮 **Part 4: Git Installation (20 minutes)**

#### **Windows**
```bash
1. Visit git-scm.com/downloads
2. Download and run installer
3. Keep clicking "Next" (defaults are good)
4. After install, restart terminal
```

#### **Mac**
```bash
# Method 1: Install from git-scm.com
# Method 2: Using Homebrew
brew install git
```

#### **Linux**
```bash
sudo apt install git
```

#### **Verification**
```bash
git --version
# Should show: git version 2.x.x
```

---

### 🏗️ **Part 5: Creating Your Project (45 minutes)**

#### **Step 1: Create Project Folder**
```bash
# Open Terminal/Command Prompt

# Navigate to where you want projects
# Windows example:
cd C:\Users\YourName\Documents

# Mac/Linux example:
cd ~/Documents

# Create project folder
mkdir rtl-gen-aiii

# Enter the folder
cd rtl-gen-aiii
```

#### **Step 2: Initialize Git**
```bash
# Turn this folder into a Git repository
git init

# You should see: Initialized empty Git repository...
```

#### **Step 3: Create Your First Files**
```bash
# Create README file
echo "# RTL-Gen AIII Project" > README.md

# Create a test Python file
echo "print('Hello, RTL-Gen AIII!')" > test.py
```

#### **Step 4: First Git Commit**
```bash
# See what files Git is tracking
git status
# Should show: README.md and test.py in red

# Add files to staging (prepare for commit)
git add README.md test.py

# Check status again - files should be green
git status

# Save a snapshot (commit)
git commit -m "Initial commit: Project setup"
```

**What just happened?**
- `git add`: Tells Git "I want to save these files"
- `git commit`: Actually saves them with a message

---

### 🔍 **Part 6: Testing Everything (30 minutes)**

#### **Test 1: Can Python run?**
```bash
python test.py
# Should output: Hello, RTL-Gen AIII!
```

#### **Test 2: Open VS Code in project**
```bash
# From inside rtl-gen-aiii folder
code .
# This opens VS Code in current folder
```

#### **Test 3: Create and run a proper test**
Create `test_setup.py` in VS Code:
```python
# test_setup.py - Run this to verify everything

import sys
import os

print("=" * 50)
print("RTL-Gen AIII Setup Verification")
print("=" * 50)

# Test Python version
print(f"\n✅ Python version: {sys.version}")

# Test current directory
print(f"✅ Working directory: {os.getcwd()}")

# Test file writing
with open("test_output.txt", "w") as f:
    f.write("Setup successful!")

if os.path.exists("test_output.txt"):
    print("✅ File writing works")
    os.remove("test_output.txt")  # Clean up

print("\n" + "=" * 50)
print("✅ Setup complete! You're ready to proceed.")
print("=" * 50)

# Simple input test
name = input("\nEnter your name to test input: ")
print(f"✅ Hello {name}! Input works!")
```

**Run it:**
```bash
python test_setup.py
```

---

### ⚠️ **Part 7: Common Problems & Solutions (30 minutes)**

**Problem 1: "Python is not recognized"**
```bash
# Symptoms: 
'python' is not recognized as an internal or external command

# Solution:
1. Uninstall Python
2. Reinstall, making ABSOLUTELY SURE to check 
   "Add Python to PATH"
3. Restart terminal
4. Try again
```

**Problem 2: "pip is not recognized"**
```bash
# Same as Problem 1 - PATH issue
# Solution: Same fix - reinstall with PATH
```

**Problem 3: VS Code doesn't show Python option**
```bash
# Solution:
1. Open VS Code
2. Press Ctrl+Shift+P (Cmd+Shift+P on Mac)
3. Type "Python: Select Interpreter"
4. Choose your Python installation
```

**Problem 4: "git is not recognized"**
```bash
# Solution:
1. Restart terminal/command prompt
2. If still not working, reinstall Git
3. During reinstall, ensure "Add to PATH" is checked
```

**Problem 5: Permission denied on Mac/Linux**
```bash
# Solution: Use sudo for installation commands
sudo command_name
```

---

### 📋 **Part 8: Daily Target Checklist**

Check off each item as you complete it:

- [x] **Python installed** and `python --version` works
- [x] **pip installed** and `pip --version` works
- [x] **VS Code installed** with extensions:
  - [x] Python extension
  - [x] Pylance extension
  - [x] Code Runner extension
  - [x] GitLens extension
- [x] **Git installed** and `git --version` works
- [x] **Project folder** created: `rtl-gen-aiii`
- [x] **Git initialized** in project folder
- [x] **First commit** made
- [x] **Test script** runs successfully
- [x] **Can open** project in VS Code

---

### 🎯 **Part 9: End-of-Day Reflection**

Answer these questions in a file called `day1_reflection.txt`:

```
1. What was the hardest part of today?
   
2. What error did you encounter and how did you fix it?
   
3. What are you most confident about now?
   
4. Rate your understanding (1-10):
   ___ Python installed and working
   ___ VS Code setup
   ___ Git basics
   ___ Overall confidence

5. Questions for tomorrow:
   
```

---

### 🚀 **Part 10: Looking Ahead to Day 2**

**Tomorrow you'll learn:**
- Python variables (storing numbers, text)
- Making decisions with if/else
- Lists and loops
- Writing your first RTL-related Python code

**To prepare:**
- [ ] Rest! This was intense
- [ ] If you had any setup issues, note them
- [ ] Be ready to write code tomorrow

---

## DAY 2: Python Basics - Variables, Data Types, Control Flow

### 🎯 **Today's Goal**
Learn Python fundamentals by building simple RTL-related examples. By tonight, you'll write code that processes design specifications.

### ⏱️ **Time Allocation (4-5 hours)**
- Theory: 1 hour
- Hands-on coding: 2.5 hours
- Practice exercises: 1 hour
- Review: 30 minutes

---

### 📚 **Part 1: Variables - Your Data Containers (30 minutes)**

**What Are Variables?**
Think of variables as labeled boxes where you store information. The label tells you what's inside.

```python
# Create a new file: day2_variables.py
# Run each section as you learn it

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
author = "RTL-Gen AIII"

print(f"\nModule: {module_name}")
print(f"Description: {description}")

# Boolean (True/False)
is_verified = False
has_errors = True
is_synthesizable = True

print(f"\nVerified? {is_verified}")
print(f"Has errors? {has_errors}")

# ============================================
# NAMING RULES (IMPORTANT!)
# ============================================

# GOOD variable names (clear, descriptive)
bit_width = 8
input_ports = 4
clock_frequency_mhz = 100

# BAD variable names (avoid these)
bw = 8  # What's "bw"? Bit width? Bandwidth?
ip = 4  # Could be intellectual property or input ports?
x = 100  # No meaning at all!

# RULES:
# 1. Can't start with number: 8bit_width = 8  # ERROR!
# 2. No spaces: bit width = 8  # ERROR!
# 3. Case-sensitive: bit_width vs Bit_width (different!)
```

**Quick Exercise:** Create variables for an 8-bit counter design
```python
# Your turn:
# 1. Create variable for counter width (8)
# 2. Create variable for counter name ("counter_8bit")
# 3. Create variable for has_reset (True)
# 4. Print all variables with descriptions

# Write your code here:
```

---

### 📦 **Part 2: Data Types - Different Kinds of Data (30 minutes)**

```python
# Continue in day2_variables.py

# ============================================
# NUMBERS (int, float)
# ============================================

# Integers for counting and indexing
port_count = 4
bit_depth = 16
register_count = 32

# Floats for measurements and ratios
operating_freq = 100.5  # MHz
power_consumption = 0.25  # Watts
area_estimate = 1200.75  # square microns

# Operations with numbers
total_pins = port_count * bit_depth
print(f"Total pins needed: {total_pins}")

# ============================================
# STRINGS (str) - Text Data
# ============================================

module_name = "alu_32bit"
verilog_code = "assign sum = a + b;"
file_path = "./outputs/alu_32bit.v"

# String operations
print(module_name.upper())        # ALU_32BIT
print(module_name.lower())        # alu_32bit
print(module_name.replace("32", "64"))  # alu_64bit

# Check string content
print("alu" in module_name)       # True
print(module_name.startswith("alu"))  # True
print(module_name.endswith(".v"))  # False

# String length
print(f"Name length: {len(module_name)} characters")

# ============================================
# LISTS - Ordered Collections
# ============================================

# List of operations
operations = ["ADD", "SUB", "AND", "OR", "XOR"]
print(f"Operations: {operations}")
print(f"First operation: {operations[0]}")  # Index 0 = first
print(f"Last operation: {operations[-1]}")  # -1 = last
print(f"Number of operations: {len(operations)}")

# Modify lists
operations.append("NOT")  # Add to end
print(f"After append: {operations}")

operations.remove("AND")  # Remove specific item
print(f"After remove: {operations}")

# List of bit widths
bit_widths = [8, 16, 32, 64]
print(f"Bit widths: {bit_widths}")

# ============================================
# DICTIONARIES - Key-Value Pairs
# ============================================

# Design specification
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

# Modify dictionary
design_spec["verified"] = True
design_spec["author"] = "RTL-Gen AIII"  # Add new key

print(f"Updated spec: {design_spec}")

# ============================================
# TYPE CHECKING
# ============================================

print(f"\nType of bit_width: {type(bit_width)}")  # <class 'int'>
print(f"Type of module_name: {type(module_name)}")  # <class 'str'>
print(f"Type of operations: {type(operations)}")  # <class 'list'>
print(f"Type of design_spec: {type(design_spec)}")  # <class 'dict'>
```

**Quick Exercise:** Create a design specification
```python
# Create a dictionary for an 8-bit counter with:
# - Name: "counter_8bit"
# - Type: "sequential" 
# - Has reset: True
# - Max count: 255

# YOUR CODE HERE
```

---

### 🔀 **Part 3: If/Else - Making Decisions (30 minutes)**

```python
# Create new file: day2_decisions.py

# ============================================
# BASIC IF STATEMENTS
# ============================================

bit_width = 16

# Simple if
if bit_width > 8:
    print("This is a wide design")
    print("Will use more resources")

# if-else
if bit_width <= 8:
    print("Small design - easy to verify")
else:
    print("Large design - complex verification needed")

# if-elif-else (multiple conditions)
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

# ============================================
# COMPARISON OPERATORS
# ============================================

a = 10
b = 20

print(f"\nComparisons:")
print(f"{a} == {b}: {a == b}")  # Equal to
print(f"{a} != {b}: {a != b}")  # Not equal
print(f"{a} < {b}: {a < b}")    # Less than
print(f"{a} > {b}: {a > b}")    # Greater than
print(f"{a} <= {b}: {a <= b}")  # Less than or equal
print(f"{a} >= {b}: {a >= b}")  # Greater than or equal

# ============================================
# LOGICAL OPERATORS (and, or, not)
# ============================================

is_combinational = True
has_clock = False
bit_width = 8

# AND - both must be True
if is_combinational and has_clock:
    print("This is sequential (has clock)")
elif is_combinational and not has_clock:
    print("This is pure combinational")

# OR - at least one must be True
if is_combinational or has_clock:
    print("Design has either combinational logic or clock")

# NOT - reverses boolean
if not has_clock:
    print("No clock signal needed")

# ============================================
# PRACTICAL EXAMPLE: Design Rule Check
# ============================================

def check_design_rules(bit_width, has_clock, operation_count):
    """
    Check if design follows basic rules
    Returns: (passes, list_of_issues)
    """
    issues = []
    
    # Rule 1: Bit width must be power of 2
    if bit_width not in [1, 2, 4, 8, 16, 32, 64]:
        issues.append(f"Bit width {bit_width} not standard")
    
    # Rule 2: Clocked designs need at least 2 operations
    if has_clock and operation_count < 2:
        issues.append("Clocked design needs at least 2 operations")
    
    # Rule 3: Bit width appropriate for operation count
    if bit_width > 32 and operation_count > 10:
        issues.append("Large design with many ops - may be complex")
    
    # Rule 4: No negative values
    if bit_width < 1 or operation_count < 0:
        issues.append("Invalid negative values")
    
    passes = len(issues) == 0
    return passes, issues

# Test the checker
test_cases = [
    (8, False, 4),   # 8-bit, combinational, 4 ops
    (16, True, 1),   # 16-bit, sequential, 1 op (should fail)
    (12, False, 5),  # 12-bit, combinational, 5 ops (warning)
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
```

---

### 🔄 **Part 4: Loops - Doing Things Repeatedly (30 minutes)**

```python
# Continue in day2_decisions.py

# ============================================
# FOR LOOPS - Iterating Over Collections
# ============================================

# Loop through a list
operations = ["ADD", "SUB", "MUL", "DIV"]
print("\nOperations:")

for op in operations:
    print(f"  - Processing {op}")
    # Add logic here

# Loop with range (generate numbers)
print("\nBit widths to generate:")
for width in range(4, 17, 4):  # start=4, stop=16, step=4
    print(f"  Generating {width}-bit design")

# Loop with index
print("\nPort list:")
port_names = ["clk", "rst", "data_in", "data_out"]
for i, port in enumerate(port_names):
    print(f"  Port {i}: {port}")

# ============================================
# WHILE LOOPS - Continue Until Condition Met
# ============================================

# Simple counter
count = 0
while count < 5:
    print(f"Count: {count}")
    count += 1  # Don't forget this!

# Simulation time example
sim_time = 0
end_time = 100
time_step = 10

print("\nSimulation timeline:")
while sim_time <= end_time:
    print(f"  Time: {sim_time} ns")
    sim_time += time_step

# ============================================
# LOOP CONTROL (break, continue)
# ============================================

# break - exit loop early
print("\nSearching for 'MUL':")
for op in operations:
    if op == "MUL":
        print(f"  Found {op}! Stopping search.")
        break
    print(f"  Checking {op}...")

# continue - skip to next iteration
print("\nEven numbers only:")
for i in range(10):
    if i % 2 != 0:  # If odd
        continue
    print(f"  {i} is even")

# ============================================
# PRACTICAL: Generating Port Lists
# ============================================

def generate_port_list(prefix, count, bit_width, direction="input"):
    """
    Generate a list of port declarations
    
    Args:
        prefix (str): Port name prefix (e.g., "data", "addr")
        count (int): Number of ports
        bit_width (int): Bit width per port
        direction (str): "input" or "output"
    
    Returns:
        list: Port declarations
    """
    ports = []
    
    for i in range(count):
        if bit_width > 1:
            port = f"{direction} [{bit_width-1}:0] {prefix}{i}"
        else:
            port = f"{direction} {prefix}{i}"
        ports.append(port)
    
    return ports

# Test the function
print("\nGenerated ports:")
data_ports = generate_port_list("data", 4, 8, "input")
for port in data_ports:
    print(f"  {port}")

addr_ports = generate_port_list("addr", 2, 16, "output")
for port in addr_ports:
    print(f"  {port}")

# ============================================
# NESTED LOOPS - Loops Inside Loops
# ============================================

print("\nOperation matrix:")
ops = ["ADD", "SUB", "AND", "OR"]
for i, op1 in enumerate(ops):
    for j, op2 in enumerate(ops):
        if i < j:  # Only upper triangle
            print(f"  {op1} + {op2}")
```

---

### 🛠️ **Part 5: Hands-On Practice (1 hour)**

Create `day2_practice.py` and complete these exercises:

```python
# day2_practice.py

# ============================================
# EXERCISE 1: Design Classifier
# ============================================
"""
Write code that classifies a design based on bit width:
- 1-8 bits: "Simple"
- 9-16 bits: "Medium"
- 17-32 bits: "Complex"
- 33+ bits: "Very Complex"
"""

bit_width = 24  # Change this to test different values

# YOUR CODE HERE
# Use if/elif/else to set complexity based on bit_width

print(f"Design with {bit_width} bits is: {complexity}")

# ============================================
# EXERCISE 2: Port Name Generator
# ============================================
"""
Generate port names for an 8-bit design.
Create a list: a0, a1, a2, a3, a4, a5, a6, a7
"""

# YOUR CODE HERE
# Use a for loop with range(8)

port_names = []
# Your loop here

print(f"Ports: {port_names}")

# ============================================
# EXERCISE 3: Design Validator
# ============================================
"""
Check if a design specification is complete.
Required fields: name, bit_width, type, ports
"""

design = {
    "name": "my_adder",
    "bit_width": 8,
    # Missing "type" and "ports"
}

required_fields = ["name", "bit_width", "type", "ports"]

# YOUR CODE HERE
# Check each required field
# If missing, add to missing_fields list

missing_fields = []
# Your checks here

if missing_fields:
    print(f"Missing fields: {missing_fields}")
else:
    print("Design spec is complete!")

# ============================================
# EXERCISE 4: Operation Counter
# ============================================
"""
Count how many operations are in a description.
Operations to look for: add, sub, and, or, xor
"""

description = "This design should add and subtract, and also do AND operations"

operations = ["add", "sub", "and", "or", "xor"]
found_ops = []

# YOUR CODE HERE
# Check if each operation is in description (lowercase)
# Add to found_ops if present

print(f"Found operations: {found_ops}")
print(f"Total count: {len(found_ops)}")

# ============================================
# EXERCISE 5: Test Vector Generator
# ============================================
"""
Generate test vectors for a 2-bit adder.
All combinations of a and b (0-3)
Format: a b sum carry
"""

print("\nTest vectors for 2-bit adder:")
print("a\tb\tsum\tcarry")

# YOUR CODE HERE
# Use nested loops: for a in range(4), for b in range(4)
# Calculate sum = a + b, carry = 1 if sum > 3 else 0
# sum_4bit = sum & 3 (mask to 2 bits)

for a in range(4):
    for b in range(4):
        # Your calculation here
        pass  # Remove this line
```

---

### 🔍 **Part 6: Common Errors & Solutions (20 minutes)**

**Error 1: IndentationError**
```python
# WRONG:
if bit_width > 8:
print("Large")  # ERROR! Must be indented

# CORRECT:
if bit_width > 8:
    print("Large")  # Indented with 4 spaces
```

**Error 2: NameError - variable not defined**
```python
# WRONG:
print(module_name)  # ERROR if module_name not defined

# CORRECT:
module_name = "adder"  # Define first
print(module_name)     # Then use
```

**Error 3: TypeError - mixing types**
```python
# WRONG:
bit_width = 8
print("Width: " + bit_width)  # ERROR! String + int

# CORRECT:
print(f"Width: {bit_width}")  # Use f-string
# OR
print("Width: " + str(bit_width))  # Convert to string
```

**Error 4: IndexError - list index out of range**
```python
ports = ["clk", "rst", "data"]
print(ports[3])  # ERROR! Only indices 0,1,2 exist

# CORRECT: Check length first
if len(ports) > 3:
    print(ports[3])
else:
    print("Port doesn't exist")
```

**Error 5: KeyError - dictionary key missing**
```python
design = {"name": "adder"}
print(design["type"])  # ERROR! 'type' key doesn't exist

# CORRECT: Use .get() with default
print(design.get("type", "unknown"))  # Returns "unknown"
```

---

### ✅ **Part 7: Daily Target Checklist**

- [ ] **Variables:** Can create and use int, float, str, bool
- [ ] **Lists:** Can create, access, modify lists
- [ ] **Dictionaries:** Can create and access key-value pairs
- [ ] **If/else:** Can write conditional logic
- [ ] **For loops:** Can iterate over ranges and lists
- [ ] **While loops:** Understand when to use them
- [ ] **Completed Exercises 1-5**
- [ ] **Can explain** when to use each data type
- [ ] **Fixed any errors** encountered

---

### 📝 **Part 8: End-of-Day Reflection**

Create `day2_reflection.txt`:

```
1. What concept was easiest today?
   
2. What took the most time to understand?
   
3. Which exercise was hardest?
   
4. Rate your understanding (1-10):
   ___ Variables and types
   ___ Lists and dictionaries
   ___ If/else statements
   ___ Loops
   ___ Overall

5. One thing I'll review tomorrow:
   
```

---

### 🔮 **Part 9: Preview of Day 3**

**Tomorrow you'll learn:**
- Functions (reusable code blocks)
- Modules (organizing code)
- First steps toward RTL generation

**To prepare:**
- [ ] Review today's exercises
- [ ] Get plenty of rest
- [ ] Come with questions

---

## DAY 3: Functions and Modules - Building Reusable Code

### 🎯 **Today's Goal**
Learn to organize code into functions and modules. By tonight, you'll build reusable components for RTL generation.

### ⏱️ **Time Allocation (4-5 hours)**
- Theory: 1 hour
- Functions coding: 1.5 hours
- Modules practice: 1 hour
- Project work: 1 hour
- Review: 30 minutes

---

### 📚 **Part 1: Why Functions? (20 minutes)**

**What Are Functions?**
Functions are like recipes - you write the steps once, then use them many times.

```
Without Functions (Bad):
print("Creating adder...")
print("Bit width: 8")
print("Ports: a, b, sum")
print("Creating adder...")  # Repeat!
print("Bit width: 16")
print("Ports: a, b, sum")

With Functions (Good):
def create_design(name, width):
    print(f"Creating {name}...")
    print(f"Bit width: {width}")
    print("Ports: a, b, sum")

create_design("adder", 8)   # One line!
create_design("adder", 16)  # One line!
```

**Benefits:**
- **Reuse**: Write once, use many times
- **Organization**: Code is grouped by purpose
- **Debugging**: Test one function at a time
- **Readability**: Function names explain what code does

---

### 🏗️ **Part 2: Creating Functions (45 minutes)**

Create `day3_functions.py`:

```python
# day3_functions.py

# ============================================
# BASIC FUNCTION STRUCTURE
# ============================================

def greet():
    """This is a docstring - describes what function does"""
    print("Hello from a function!")

# Call the function
greet()  # Output: Hello from a function!

# ============================================
# FUNCTIONS WITH PARAMETERS
# ============================================

def generate_module_name(component_type, bit_width):
    """
    Generate a standardized module name
    
    Args:
        component_type (str): Type (adder, counter, etc.)
        bit_width (int): Bit width of design
    
    Returns:
        str: Formatted module name
    """
    module_name = f"{component_type}_{bit_width}bit"
    return module_name

# Use the function
name1 = generate_module_name("adder", 8)
print(name1)  # adder_8bit

name2 = generate_module_name("counter", 16)
print(name2)  # counter_16bit

# ============================================
# FUNCTIONS WITH MULTIPLE PARAMETERS
# ============================================

def create_port_declaration(direction, name, bit_width=1):
    """
    Create a Verilog port declaration
    
    Args:
        direction (str): "input", "output", or "inout"
        name (str): Port name
        bit_width (int): Width (1 for single bit)
    
    Returns:
        str: Formatted port declaration
    """
    if bit_width == 1:
        return f"    {direction} {name}"
    else:
        return f"    {direction} [{bit_width-1}:0] {name}"

# Test different calls
print(create_port_declaration("input", "clk"))           # Single bit
print(create_port_declaration("input", "data", 8))       # 8-bit bus
print(create_port_declaration("output", "result", 16))   # 16-bit bus

# ============================================
# DEFAULT PARAMETERS
# ============================================

def create_design_spec(name, bit_width=8, design_type="combinational"):
    """
    Create design specification with defaults
    
    Args:
        name (str): Module name
        bit_width (int): Bit width (default: 8)
        design_type (str): Type (default: "combinational")
    
    Returns:
        dict: Design specification
    """
    spec = {
        "name": name,
        "bit_width": bit_width,
        "type": design_type,
        "created": "2026-02-09"
    }
    return spec

# Call with all parameters
spec1 = create_design_spec("adder", 16, "combinational")
print(f"\nSpec1: {spec1}")

# Call with defaults (uses bit_width=8, type="combinational")
spec2 = create_design_spec("counter")
print(f"Spec2: {spec2}")

# Call with named parameters (clearer)
spec3 = create_design_spec(
    name="alu",
    bit_width=32,
    design_type="sequential"
)
print(f"Spec3: {spec3}")

# ============================================
# RETURNING MULTIPLE VALUES
# ============================================

def analyze_design(description):
    """
    Analyze design description and return multiple insights
    
    Returns:
        tuple: (component_type, bit_width, has_clock)
    """
    desc = description.lower()
    
    # Default values
    component = "unknown"
    width = 8
    has_clock = "clock" in desc or "clk" in desc
    
    # Detect component
    if "adder" in desc:
        component = "adder"
    elif "counter" in desc:
        component = "counter"
    elif "alu" in desc:
        component = "alu"
    
    # Detect bit width
    for w in [64, 32, 16, 8, 4]:
        if f"{w}-bit" in desc or f"{w} bit" in desc:
            width = w
            break
    
    return component, width, has_clock

# Test the function
desc = "Create a 16-bit adder with clock"
comp, width, clock = analyze_design(desc)
print(f"\nAnalysis: {comp}, {width}bit, clock={clock}")

# ============================================
# DOCSTRINGS - Documenting Functions
# ============================================

def validate_bit_width(width):
    """
    Validate if bit width is acceptable for hardware design.
    
    A good bit width should be:
    - Positive integer
    - Power of 2 (1, 2, 4, 8, 16, 32, 64)
    - Not too large for simulation
    
    Args:
        width: Integer to validate
    
    Returns:
        tuple: (is_valid, message)
    
    Examples:
        >>> validate_bit_width(8)
        (True, "Valid bit width")
        >>> validate_bit_width(3)
        (False, "Bit width must be power of 2")
    """
    if not isinstance(width, int):
        return False, "Bit width must be integer"
    
    if width < 1:
        return False, "Bit width must be positive"
    
    if width > 64:
        return False, "Bit width too large (max 64)"
    
    # Check if power of 2
    if (width & (width - 1)) != 0:
        return False, "Bit width must be power of 2"
    
    return True, "Valid bit width"

# Test the function
test_widths = [8, 16, 3, 0, 128]
for w in test_widths:
    valid, msg = validate_bit_width(w)
    print(f"Width {w}: {msg}")

# See the docstring
help(validate_bit_width)  # Shows documentation
```

---

### 🔨 **Part 3: Function Composition (30 minutes)**

```python
# Continue in day3_functions.py

# ============================================
# BUILDING COMPLEX FUNCTIONS FROM SIMPLE ONES
# ============================================

def extract_bit_width(description):
    """Extract bit width from description"""
    desc = description.lower()
    for width in [64, 32, 16, 8, 4]:
        if f"{width}-bit" in desc or f"{width} bit" in desc:
            return width
    return 8  # default

def extract_component(description):
    """Extract component type from description"""
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
    """Extract ALU operations from description"""
    desc = description.lower()
    ops = []
    all_ops = ["add", "sub", "and", "or", "xor", "not"]
    
    for op in all_ops:
        if op in desc:
            ops.append(op.upper())
    
    return ops

def parse_design_request(description):
    """
    Main parsing function that USES the smaller functions
    This is COMPOSITION - building complex from simple
    """
    result = {
        "original": description,
        "bit_width": extract_bit_width(description),
        "component": extract_component(description),
        "operations": extract_operations(description),
        "has_clock": "clock" in description.lower() or "clk" in description.lower(),
        "is_valid": True,
        "warnings": []
    }
    
    # Add warnings if needed
    if result["component"] == "unknown":
        result["warnings"].append("Could not identify component type")
    
    if result["component"] == "alu" and not result["operations"]:
        result["warnings"].append("ALU specified but no operations found")
    
    result["is_valid"] = len(result["warnings"]) == 0
    
    return result

# Test the composed function
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
    if result['operations']:
        print(f"Ops: {', '.join(result['operations'])}")
    if result['warnings']:
        print(f"Warnings: {result['warnings']}")
```

---

### 📦 **Part 4: Creating and Using Modules (45 minutes)**

Create a new file: `rtl_utils.py`

```python
# rtl_utils.py
"""
RTL Generation Utility Functions
This module contains helper functions for RTL code generation
"""

# ============================================
# VALIDATION FUNCTIONS
# ============================================

def is_power_of_two(n):
    """Check if a number is a power of two"""
    if n <= 0:
        return False
    return (n & (n - 1)) == 0

def validate_component_type(comp_type):
    """Check if component type is supported"""
    supported = ["adder", "counter", "alu", "multiplexer", "register"]
    return comp_type.lower() in supported

def get_supported_components():
    """Return list of supported components"""
    return ["adder", "counter", "alu", "multiplexer", "register"]

# ============================================
# GENERATION FUNCTIONS
# ============================================

def generate_module_header(module_name):
    """Generate Verilog module header"""
    return f"module {module_name}("

def generate_module_footer():
    """Generate Verilog module footer"""
    return "endmodule"

def generate_port_list(ports_config):
    """
    Generate list of port declarations
    
    Args:
        ports_config: List of dicts with keys:
            - direction: "input"/"output"
            - name: port name
            - width: bit width (default 1)
    
    Returns:
        list: Formatted port declarations
    """
    ports = []
    
    for i, port in enumerate(ports_config):
        direction = port['direction']
        name = port['name']
        width = port.get('width', 1)
        
        if width > 1:
            decl = f"    {direction} [{width-1}:0] {name}"
        else:
            decl = f"    {direction} {name}"
        
        # Add comma for all but last port
        if i < len(ports_config) - 1:
            decl += ","
        
        ports.append(decl)
    
    return ports

# ============================================
# ANALYSIS FUNCTIONS
# ============================================

def estimate_gates(bit_width, component_type):
    """
    Rough estimate of gate count
    """
    base_counts = {
        "adder": bit_width * 5,
        "counter": bit_width * 4,
        "alu": bit_width * 10,
        "multiplexer": bit_width * 2,
        "register": bit_width * 6
    }
    
    return base_counts.get(component_type, bit_width * 3)

def suggest_test_cases(bit_width, component_type):
    """
    Suggest number of test cases needed
    """
    if component_type == "adder":
        return min(100, 2 ** (bit_width * 2))
    elif component_type == "counter":
        return min(50, 2 ** bit_width)
    else:
        return min(20, 2 ** bit_width)

# ============================================
# HELPER FUNCTIONS
# ============================================

def format_verilog_code(code_lines):
    """Format Verilog code with proper indentation"""
    return "\n".join(code_lines)

def add_comment(comment):
    """Add comment to Verilog code"""
    return f"// {comment}"

def create_filename(module_name):
    """Create standard filename for module"""
    return f"{module_name}.v"
```

Now create `day3_modules.py` to use the module:

```python
# day3_modules.py
# Using the rtl_utils module

# Method 1: Import entire module
import rtl_utils

# Use functions with module prefix
print("Power of 2 checks:")
print(f"8 is power of 2: {rtl_utils.is_power_of_two(8)}")
print(f"12 is power of 2: {rtl_utils.is_power_of_two(12)}")

# Method 2: Import specific functions
from rtl_utils import generate_port_list, estimate_gates

# Define ports for an adder
adder_ports = [
    {"direction": "input", "name": "a", "width": 8},
    {"direction": "input", "name": "b", "width": 8},
    {"direction": "output", "name": "sum", "width": 8},
    {"direction": "output", "name": "carry"}
]

# Generate port list
print("\nAdder ports:")
ports = generate_port_list(adder_ports)
for port in ports:
    print(f"  {port}")

# Estimate gates
gate_count = estimate_gates(8, "adder")
print(f"\nEstimated gates: {gate_count}")

# Method 3: Import with alias
import rtl_utils as ru

components = ru.get_supported_components()
print(f"\nSupported components: {components}")

test_cases = ru.suggest_test_cases(8, "adder")
print(f"Suggested test cases: {test_cases}")

# ============================================
# BUILDING A COMPLETE DESIGN
# ============================================

def create_adder_design(bit_width):
    """Create complete adder design using utility functions"""
    
    # Validate
    if not ru.is_power_of_two(bit_width):
        print(f"Warning: {bit_width} not power of 2")
    
    # Create ports
    ports = [
        {"direction": "input", "name": "a", "width": bit_width},
        {"direction": "input", "name": "b", "width": bit_width},
        {"direction": "output", "name": "sum", "width": bit_width},
        {"direction": "output", "name": "carry"}
    ]
    
    # Build module
    module_name = f"adder_{bit_width}bit"
    code_lines = []
    
    code_lines.append(ru.add_comment(f"{bit_width}-bit Adder"))
    code_lines.append(f"module {module_name}(")
    code_lines.extend(ru.generate_port_list(ports))
    code_lines.append(");")
    code_lines.append("")
    code_lines.append(f"    // {bit_width}-bit addition")
    code_lines.append(f"    assign {{carry, sum}} = a + b;")
    code_lines.append("")
    code_lines.append("endmodule")
    
    code = ru.format_verilog_code(code_lines)
    
    return code, ru.estimate_gates(bit_width, "adder")

# Test it
code, gates = create_adder_design(16)
print(f"\nGenerated Code ({gates} estimated gates):")
print(code)
```

---

### 🛠️ **Part 5: Hands-On Practice (1 hour)**

Create `day3_practice.py`:

```python
# day3_practice.py

# ============================================
# EXERCISE 1: Module Name Generator
# ============================================
"""
Write a function that creates standardized module names
Format: {type}_{width}bit_{suffix}
Example: adder_8bit_rtl
"""

def generate_module_name(comp_type, width, suffix="rtl"):
    # YOUR CODE HERE
    pass

# Test
print(generate_module_name("adder", 8))          # adder_8bit_rtl
print(generate_module_name("counter", 16, "tb")) # counter_16bit_tb

# ============================================
# EXERCISE 2: Input Validator
# ============================================
"""
Write a function that validates design input
Rules:
- Not empty
- At least 10 characters
- Contains valid component type
Returns: (is_valid, error_message)
"""

valid_components = ["adder", "counter", "alu", "mux"]

def validate_design_input(description):
    # YOUR CODE HERE
    pass

# Test
print(validate_design_input(""))  # (False, "Empty input")
print(validate_design_input("8-bit"))  # (False, "No component type")
print(validate_design_input("Create an 8-bit adder"))  # (True, "Valid")

# ============================================
# EXERCISE 3: Port Counter
# ============================================
"""
Write a function that counts ports in a Verilog module
Count lines with 'input' or 'output'
"""

def count_ports(verilog_code):
    # YOUR CODE HERE
    pass

# Test
code = """
module test(
    input clk,
    input rst,
    output [7:0] data
);
endmodule
"""

print(f"Port count: {count_ports(code)}")  # Should be 3

# ============================================
# EXERCISE 4: Design Cost Estimator
# ============================================
"""
Create functions to estimate design cost:

estimate_area(bit_width, comp_type) -> area in sq microns
    - adder: width * 100
    - counter: width * 150
    - alu: width * 300
    - default: width * 200

estimate_power(area, frequency) -> power in mW
    - power = area * frequency * 0.001
"""

def estimate_area(bit_width, comp_type):
    # YOUR CODE HERE
    pass

def estimate_power(area, frequency_mhz):
    # YOUR CODE HERE
    pass

# Test
area = estimate_area(16, "adder")
power = estimate_power(area, 100)
print(f"16-bit adder: area={area}, power={power:.2f}mW")

# ============================================
# EXERCISE 5: Module System
# ============================================
"""
Create a module called 'verilog_helpers.py' with:
1. add_comment(text) - returns formatted comment
2. indent_line(line, spaces=4) - indents code
3. create_always_block(sensitivity, statements) - creates always block

Then import and use it here
"""

# Create verilog_helpers.py first, then import here
# import verilog_helpers as vh

# Test your helpers
# comment = vh.add_comment("This is a test")
# indented = vh.indent_line("$display('hello');")
# always = vh.create_always_block("@(posedge clk)", ["q <= d;"])
```

---

### 🔍 **Part 6: Common Errors & Solutions (20 minutes)**

**Error 1: Missing return statement**
```python
# WRONG:
def add(a, b):
    result = a + b
    # No return!

total = add(5, 3)
print(total)  # Prints: None

# CORRECT:
def add(a, b):
    result = a + b
    return result
```

**Error 2: Modifying list in function**
```python
# WRONG - modifies original!
def add_port(ports, new_port):
    ports.append(new_port)  # Changes original list

my_ports = ["clk", "rst"]
add_port(my_ports, "data")
print(my_ports)  # Changed! ["clk", "rst", "data"]

# CORRECT - returns new list
def add_port(ports, new_port):
    new_ports = ports.copy()
    new_ports.append(new_port)
    return new_ports
```

**Error 3: Module not found**
```python
# When importing:
import my_module

# Error if:
# 1. my_module.py doesn't exist
# 2. my_module.py not in same directory
# 3. Typo in name

# Solution:
# - Check file exists
# - Check spelling
# - Check current directory: import os; print(os.getcwd())
```

**Error 4: Function defined after use**
```python
# WRONG:
result = add(5, 3)  # Error! add not defined yet

def add(a, b):
    return a + b

# CORRECT: Define before use
def add(a, b):
    return a + b

result = add(5, 3)
```

---

### ✅ **Part 7: Daily Target Checklist**

- [ ] **Functions basics:** Can define and call functions
- [ ] **Parameters:** Use parameters and return values
- [ ] **Default values:** Create functions with defaults
- [ ] **Multiple returns:** Return and unpack tuples
- [ ] **Docstrings:** Document functions properly
- [ ] **Module creation:** Created rtl_utils.py
- [ ] **Module import:** Imported and used functions
- [ ] **Function composition:** Combined simple functions
- [ ] **Completed Exercises 1-5**

---

### 📝 **Part 8: End-of-Day Reflection**

Create `day3_reflection.txt`:

```
1. What's the most useful function I wrote today?
   
2. What was tricky about modules?
   
3. How will I use functions in RTL-Gen AIII?
   
4. Rate your understanding (1-10):
   ___ Writing functions
   ___ Return values
   ___ Modules
   ___ Function composition
   ___ Overall

5. Questions for tomorrow:
   
```

---

### 🎉 **Part 9: Week 1 Days 1-3 Complete!**

**You've learned:**
- ✅ Day 1: Complete development environment
- ✅ Day 2: Python variables, data types, control flow
- ✅ Day 3: Functions, modules, code organization

**What's next:**
- Day 4: File operations and string manipulation
- Day 5: JSON and requests (API basics)
- Day 6-7: Weekend project - Build RTL Assistant

**Rest well! You've earned it.**



