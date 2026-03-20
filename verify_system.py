#!/usr/bin/env python3
"""
System Verification Script for RTL-Gen AI
Checks all required modules and components are available
"""

import sys
import importlib
from pathlib import Path

def check_module(module_name):
    """Check if a module can be imported"""
    try:
        importlib.import_module(module_name)
        print(f"✅ {module_name}")
        return True
    except ImportError as e:
        print(f"❌ {module_name}: {e}")
        return False

def check_file(file_path):
    """Check if a file exists"""
    path = Path(file_path)
    if path.exists():
        print(f"✅ File: {file_path}")
        return True
    else:
        print(f"❌ File: {file_path} (not found)")
        return False

print("=" * 60)
print("🔍 RTL-GEN AI SYSTEM VERIFICATION")
print("=" * 60)

# Check Python version
print(f"\n📌 Python Version: {sys.version.split()[0]}")
if sys.version_info >= (3, 9):
    print("✅ Python version OK (3.9+)")
else:
    print("❌ Python version too old - need 3.9+")

# Check core modules
print("\n📦 CORE MODULES:")
print("-" * 60)

core_modules = [
    'python.llm_client',
    'python.input_processor',
    'python.prompt_builder',
    'python.extraction_pipeline',
    'python.code_formatter',
    'python.verification_engine',
    'python.cache_manager',
    'python.mock_llm',
    'python.verilog_generator',
]

core_ok = 0
for module in core_modules:
    if check_module(module):
        core_ok += 1

print(f"\nCore Modules: {core_ok}/{len(core_modules)} available")

# Check dependencies
print("\n📚 DEPENDENCIES:")
print("-" * 60)

dependencies = [
    'streamlit',
    'anthropic',
    'requests',
    'python-dotenv',
    'pytest',
]

deps_ok = 0
for dep in dependencies:
    try:
        importlib.import_module(dep.replace('-', '_'))
        print(f"✅ {dep}")
        deps_ok += 1
    except ImportError:
        print(f"❌ {dep} (not installed)")

print(f"\nDependencies: {deps_ok}/{len(dependencies)} installed")

# Check key files
print("\n📄 KEY FILES:")
print("-" * 60)

key_files = [
    'app.py',
    'requirements.txt',
    'python/__init__.py',
    'python/llm_client.py',
    'python/mock_llm.py',
]

files_ok = 0
for file in key_files:
    if check_file(file):
        files_ok += 1

print(f"\nKey Files: {files_ok}/{len(key_files)} present")

# Summary
print("\n" + "=" * 60)
print("📊 VERIFICATION SUMMARY")
print("=" * 60)

total_checks = len(core_modules) + len(dependencies) + len(key_files)
passed_checks = core_ok + deps_ok + files_ok

print(f"\nTotal Checks: {passed_checks}/{total_checks}")
print(f"Status: {'✅ READY' if passed_checks == total_checks else '⚠️ NEEDS ATTENTION'}")

if passed_checks < total_checks:
    print("\n🔧 RECOMMENDED ACTIONS:")
    print("1. Install missing dependencies: pip install -r requirements.txt")
    print("2. Try: pip install anthropic streamlit")
    print("3. Check Python path: python -c \"import sys; print(sys.path)\"")

print("\n" + "=" * 60)
print("✅ Next Step: Run 'python test_mock.py'")
print("=" * 60)
