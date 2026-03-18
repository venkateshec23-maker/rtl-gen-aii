"""
Results Parser for RTL-Gen AI
Parses simulation output to determine pass/fail status.

Features:
1. Detect pass/fail patterns
2. Count tests passed/failed
3. Extract error messages
4. Identify test patterns

Usage:
    parser = ResultsParser()
    result = parser.parse(simulation_output)
    
    if result['passed']:
        print(f"Tests passed: {result['tests_passed']}")
"""

import re
from typing import Dict, List, Tuple

from python.config import DEBUG_MODE


class ResultsParser:
    """
    Parses simulation output for test results.
    
    Looks for patterns like:
    - "PASS" / "FAIL"
    - "Test X: PASS"
    - "All tests passed"
    - "ERROR: ..."
    - Test statistics
    
    Usage:
        parser = ResultsParser()
        result = parser.parse(output)
    """
    
    def __init__(self, debug: bool = None):
        """
        Initialize results parser.
        
        Args:
            debug: Enable debug output
        """
        self.debug = debug if debug is not None else DEBUG_MODE
        
        # Patterns for pass/fail detection
        self.pass_patterns = [
            r'\bPASS\b',
            r'\bpassed\b',
            r'\[PASS\]',
            r'SUCCESS',
            r'All tests passed',
        ]
        
        self.fail_patterns = [
            r'\bFAIL\b',
            r'\bfailed\b',
            r'\[FAIL\]',
            r'ERROR',
            r'FAILED',
            r'Test.*failed',
        ]
        
        if self.debug:
            print("ResultsParser initialized")
    
    def parse(self, output: str) -> Dict:
        """
        Parse simulation output.
        
        Args:
            output: Simulation output text
            
        Returns:
            dict: {
                'passed': bool (overall pass/fail),
                'tests_passed': int,
                'tests_failed': int,
                'total_tests': int,
                'errors': list,
                'pass_lines': list,
                'fail_lines': list,
            }
        """
        if self.debug:
            print(f"\nParsing simulation output ({len(output)} chars)")
        
        lines = output.split('\n')
        
        pass_lines = []
        fail_lines = []
        errors = []
        
        # Parse line by line
        for line in lines:
            line_stripped = line.strip()
            if not line_stripped:
                continue
            
            # Check for pass patterns
            for pattern in self.pass_patterns:
                if re.search(pattern, line_stripped, re.IGNORECASE):
                    pass_lines.append(line_stripped)
                    break
            
            # Check for fail patterns
            for pattern in self.fail_patterns:
                if re.search(pattern, line_stripped, re.IGNORECASE):
                    fail_lines.append(line_stripped)
                    break
            
            # Check for explicit errors
            if 'error' in line_stripped.lower():
                errors.append(line_stripped)
        
        # Determine overall pass/fail
        tests_passed = len(pass_lines)
        tests_failed = len(fail_lines)
        total_tests = tests_passed + tests_failed
        
        # Overall pass if:
        # 1. No explicit failures found
        # 2. At least some passes OR no errors
        passed = (tests_failed == 0) and (tests_passed > 0 or len(errors) == 0)
        
        # Special case: If output contains "All tests passed"
        if any('all tests passed' in line.lower() for line in lines):
            passed = True
        
        # Special case: If no tests but also no errors, consider it a pass
        # (some testbenches just run without explicit PASS/FAIL)
        if total_tests == 0 and len(errors) == 0 and len(output) > 0:
            passed = True
        
        if self.debug:
            print(f"  Tests passed: {tests_passed}")
            print(f"  Tests failed: {tests_failed}")
            print(f"  Errors: {len(errors)}")
            print(f"  Overall: {'PASS' if passed else 'FAIL'}")
        
        return {
            'passed': passed,
            'tests_passed': tests_passed,
            'tests_failed': tests_failed,
            'total_tests': total_tests,
            'errors': errors,
            'pass_lines': pass_lines,
            'fail_lines': fail_lines,
        }


# ============================================================================
# SELF-TEST
# ============================================================================

if __name__ == "__main__":
    print("Results Parser Self-Test\n")
    print("=" * 70)
    
    parser = ResultsParser(debug=True)
    
    # Test 1: All tests passed
    print("\n1. Testing all passed:")
    print("-" * 70)
    
    output1 = """
VCD info: dumpfile waveform.vcd opened for output.
Testing 8-bit adder
Test 1: 5 + 3 = 8 PASS
Test 2: 10 + 20 = 30 PASS
Test 3: 255 + 1 = 0 (with carry) PASS
All tests passed!
"""
    
    result1 = parser.parse(output1)
    print(f"\nPassed: {result1['passed']}")
    print(f"Tests passed: {result1['tests_passed']}/{result1['total_tests']}")
    
    # Test 2: Some tests failed
    print("\n2. Testing with failures:")
    print("-" * 70)
    
    output2 = """
Testing ALU
Test 1: ADD operation PASS
Test 2: SUB operation FAIL (expected 5, got 3)
Test 3: AND operation PASS
ERROR: 1 test failed
"""
    
    result2 = parser.parse(output2)
    print(f"\nPassed: {result2['passed']}")
    print(f"Tests passed: {result2['tests_passed']}/{result2['total_tests']}")
    print(f"Failed tests: {result2['tests_failed']}")
    print(f"Errors: {result2['errors']}")
    
    # Test 3: No explicit PASS/FAIL but successful
    print("\n3. Testing implicit success:")
    print("-" * 70)
    
    output3 = """
VCD info: dumpfile waveform.vcd opened for output.
Counter test starting
Count: 0
Count: 1
Count: 2
Simulation complete
"""
    
    result3 = parser.parse(output3)
    print(f"\nPassed: {result3['passed']}")
    print(f"Tests: {result3['total_tests']}")
    
    print("\n" + "=" * 70)
    print("Self-test complete!")
    print("=" * 70)
