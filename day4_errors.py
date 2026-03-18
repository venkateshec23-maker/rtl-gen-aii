# day4_errors.py - Error Handling

import os

print("=" * 50)
print("ERROR HANDLING")
print("=" * 50)


def safe_read_file(filename):
    """Read file safely with error handling"""
    try:
        with open(filename, 'r') as f:
            content = f.read()
        return True, content
    except FileNotFoundError:
        return False, f"File '{filename}' not found"
    except PermissionError:
        return False, f"No permission to read '{filename}'"
    except UnicodeDecodeError:
        return False, f"File '{filename}' has encoding issues"
    except Exception as e:
        return False, f"Unexpected error: {str(e)}"


files_to_test = ['adder_8bit.v', 'nonexistent.txt', 'test.txt']

for file in files_to_test:
    print(f"\nReading: {file}")
    success, result = safe_read_file(file)
    if success:
        print(f"✓ Success! First 50 chars: {result[:50]}...")
    else:
        print(f"✗ Error: {result}")


def safe_write_file(filename, content, mode='w'):
    """Write file safely with error handling"""
    try:
        directory = os.path.dirname(filename)
        if directory and not os.path.exists(directory):
            os.makedirs(directory, exist_ok=True)

        with open(filename, mode, encoding='utf-8') as f:
            f.write(content)
        return True, f"Successfully wrote to {filename}"
    except PermissionError:
        return False, f"No permission to write to {filename}"
    except IsADirectoryError:
        return False, f"{filename} is a directory"
    except Exception as e:
        return False, f"Write error: {str(e)}"


success, message = safe_write_file("outputs/test.txt", "Test content")
print(f"\nWrite test: {message}")


def validate_verilog_file(filename):
    """Basic validation of Verilog file"""
    success, content = safe_read_file(filename)
    if not success:
        return False, content

    issues = []

    if 'module' not in content:
        issues.append("Missing 'module' keyword")
    if 'endmodule' not in content:
        issues.append("Missing 'endmodule' keyword")
    if content.count('(') != content.count(')'):
        issues.append("Unbalanced parentheses")

    if issues:
        return False, issues
    return True, "Valid Verilog file"


valid, result = validate_verilog_file("adder_8bit.v")
if valid:
    print(f"\n✓ {result}")
else:
    print("\n✗ Issues found:")
    if isinstance(result, list):
        for issue in result:
            print(f"  - {issue}")
    else:
        print(f"  - {result}")
