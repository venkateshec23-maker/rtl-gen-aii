"""
Run All Tests Script
Executes complete test suite with reporting.

Usage: python scripts/run_all_tests.py
"""

import subprocess
import sys
import os
from pathlib import Path


def run_pytest():
    """Run pytest test suite."""
    print("=" * 70)
    print("RUNNING PYTEST SUITE")
    print("=" * 70)
    
    result = subprocess.run(
        ["pytest", "tests/", "-v", "--tb=short", "--cov=python", "--cov-report=term-missing"],
        capture_output=False
    )
    
    return result.returncode == 0


def run_self_tests():
    """Run self-tests for each module."""
    print("\n" + "=" * 70)
    print("RUNNING MODULE SELF-TESTS")
    print("=" * 70)
    
    modules = [
        "python/input_processor.py",
        "python/prompt_builder.py",
        "python/code_extractor.py",
        "python/compilation_manager.py",
        "python/simulation_runner.py",
        "python/verification_engine.py",
        "python/testbench_generator.py",
        "python/rtl_generator.py",
    ]
    
    passed = 0
    failed = 0
    
    env = os.environ.copy()
    env["PYTHONPATH"] = str(Path.cwd())
    
    for module in modules:
        print(f"\n{module}:")
        result = subprocess.run([sys.executable, module], capture_output=True, env=env)
        
        if result.returncode == 0:
            print("  ✓ PASSED")
            passed += 1
        else:
            print("  ✗ FAILED")
            failed += 1
            if result.stderr:
                print(f"  Error: {result.stderr.decode()[:200]}")
    
    print(f"\nSelf-tests: {passed} passed, {failed} failed")
    
    return failed == 0


def run_integration_tests():
    """Run integration tests."""
    print("\n" + "=" * 70)
    print("RUNNING INTEGRATION TESTS")
    print("=" * 70)
    
    test_files = [
        "test_complete_workflow.py",
        "test_with_testbench_gen.py",
    ]
    
    passed = 0
    failed = 0
    
    env = os.environ.copy()
    env["PYTHONPATH"] = str(Path.cwd())
    
    for test_file in test_files:
        if Path(test_file).exists():
            print(f"\n{test_file}:")
            result = subprocess.run([sys.executable, test_file], capture_output=True, env=env)
            
            if result.returncode == 0:
                print("  ✓ PASSED")
                passed += 1
            else:
                print("  ✗ FAILED")
                failed += 1
        else:
            print(f"\n{test_file}: SKIPPED (not found)")
    
    print(f"\nIntegration tests: {passed} passed, {failed} failed")
    
    return failed == 0


def run_qa_checks():
    """Run quality assurance checks."""
    print("\n" + "=" * 70)
    print("RUNNING QA CHECKS")
    print("=" * 70)
    
    env = os.environ.copy()
    env["PYTHONPATH"] = str(Path.cwd())
    
    result = subprocess.run([sys.executable, "scripts/qa_check.py"], capture_output=False, env=env)
    
    return result.returncode == 0


def main():
    """Run all tests and report results."""
    print("\n" + "*" * 70)
    print("COMPLETE TEST SUITE")
    print("*" * 70)
    
    results = {
        'pytest': run_pytest(),
        'self_tests': run_self_tests(),
        'integration': run_integration_tests(),
        'qa': run_qa_checks(),
    }
    
    print("\n" + "*" * 70)
    print("FINAL RESULTS")
    print("*" * 70)
    
    for test_name, passed in results.items():
        status = "✓ PASSED" if passed else "✗ FAILED"
        print(f"{test_name}: {status}")
    
    all_passed = all(results.values())
    
    print("\n" + "*" * 70)
    if all_passed:
        print("🎉 ALL TESTS PASSED!")
    else:
        print("❌ SOME TESTS FAILED")
    print("*" * 70)
    
    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(main())
