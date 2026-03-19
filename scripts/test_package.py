"""
Test Package Installation Script

This script verifies that the module structure and entry points
are correctly reachable after installation via setup.py or pyproject.toml.

Run with: python scripts/test_package.py
"""

import sys
import importlib

def test_imports():
    """Test importing all major submodules."""
    modules = [
        "python.rtl_generator",
        "python.batch_processor",
        "python.cache_manager",
        "python.performance_monitor",
    ]
    
    print("Testing core module imports...")
    success = True
    for mod in modules:
        try:
            importlib.import_module(mod)
            print(f" ✓ Imported {mod}")
        except ImportError as e:
            print(f" ✗ Failed to import {mod}: {e}")
            success = False
            
    return success

def main():
    print("====================================")
    print("PACKAGE VERIFICATION TEST")
    print("====================================")
    
    if test_imports():
        print("\nAll package modules imported successfully.")
        sys.exit(0)
    else:
        print("\nPackage import tests failed.")
        sys.exit(1)

if __name__ == "__main__":
    main()
