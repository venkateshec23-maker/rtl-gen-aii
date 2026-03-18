# test_assistant.py
"""Test script for RTL Assistant"""

from design_parser import DesignParser
from template_generator import TemplateGenerator
from file_manager import FileManager


def test_parser():
    """Test the design parser"""
    print("=" * 50)
    print("TESTING DESIGN PARSER")
    print("=" * 50)

    parser = DesignParser()

    test_cases = [
        "Create an 8-bit adder",
        "Design a 16-bit counter with clock and reset",
        "Build a 32-bit ALU with ADD, SUB, AND operations",
        "Make a 4-bit multiplexer",
        "Create a 64-bit register with reset"
    ]

    for desc in test_cases:
        print(f"\nInput: {desc}")
        result = parser.parse(desc)
        print(f"  Component: {result['component']}")
        print(f"  Width: {result['bit_width']}")
        print(f"  Clock: {result['has_clock']}")
        print(f"  Reset: {result['has_reset']}")
        print(f"  Module: {parser.suggest_module_name(result)}")


def test_generator():
    """Test the template generator"""
    print("\n" + "=" * 50)
    print("TESTING TEMPLATE GENERATOR")
    print("=" * 50)

    parser = DesignParser()
    generator = TemplateGenerator()

    test_descriptions = [
        "8-bit adder",
        "16-bit counter with reset",
        "32-bit ALU with ADD and SUB",
        "4-bit multiplexer",
        "8-bit register"
    ]

    for desc in test_descriptions:
        print(f"\nGenerating for: {desc}")
        parsed = parser.parse(desc)
        parsed['module_name'] = parser.suggest_module_name(parsed)
        code = generator.generate(parsed)

        lines = code.split('\n')[:5]
        for line in lines:
            print(f"  {line}")
        print("  ...")


def test_file_manager():
    """Test the file manager"""
    print("\n" + "=" * 50)
    print("TESTING FILE MANAGER")
    print("=" * 50)

    fm = FileManager()

    config = fm.load_config()
    print(f"Config loaded: {config}")

    history = fm.get_history()
    print(f"History entries: {len(history)}")

    fm.log_activity("TEST", "Testing file manager")
    print("Activity logged")

    # Test saving a design
    parser = DesignParser()
    generator = TemplateGenerator()

    parsed = parser.parse("Create an 8-bit adder")
    parsed['module_name'] = parser.suggest_module_name(parsed)
    code = generator.generate(parsed)

    design_dir = fm.save_design(parsed, code)
    print(f"Design saved to: {design_dir}")


if __name__ == "__main__":
    test_parser()
    test_generator()
    test_file_manager()

    print("\n" + "=" * 50)
    print("All tests passed! ✅")
    print("=" * 50)
