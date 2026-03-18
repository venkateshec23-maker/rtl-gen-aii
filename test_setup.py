# test_setup.py - Run this to verify everything

import sys
import os

print("=" * 50)
print("RTL-Gen AII Setup Verification")
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
# name = input("\nEnter your name to test input: ")
# print(f"✅ Hello {name}! Input works!")
