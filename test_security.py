"""
Security Test Suite

Tests security measures in RTL-Gen AI.

Usage: python test_security.py
"""

from python.security_auditor import SecurityAuditor
from python.input_sanitizer import InputSanitizer


def test_input_sanitization():
    """Test input sanitization."""
    print("=" * 70)
    print("TEST 1: INPUT SANITIZATION")
    print("=" * 70)
    
    sanitizer = InputSanitizer()
    
    test_cases = [
        ("Normal 8-bit counter", True),
        ("<script>alert('xss')</script>", False),
        ("../../../etc/passwd", False),
        ("eval(malicious_code)", False),
        ("A" * 10000, False),
        ("", False),
    ]
    
    passed = 0
    
    for input_text, should_pass in test_cases:
        try:
            result = sanitizer.sanitize_description(input_text)
            if should_pass:
                print(f"  ✓ Accepted: '{input_text[:30]}...'")
                passed += 1
            else:
                print(f"  ✗ Should have rejected: '{input_text[:30]}...'")
        except ValueError:
            if not should_pass:
                print(f"  ✓ Correctly rejected: '{input_text[:30]}...'")
                passed += 1
            else:
                print(f"  ✗ Should have accepted: '{input_text[:30]}...'")
    
    print(f"\nPassed: {passed}/{len(test_cases)}")
    
    return passed == len(test_cases)


def test_module_name_validation():
    """Test module name validation."""
    print("\n" + "=" * 70)
    print("TEST 2: MODULE NAME VALIDATION")
    print("=" * 70)
    
    sanitizer = InputSanitizer()
    
    test_cases = [
        ("my_module", True),
        ("Module123", True),
        ("_internal", True),
        ("123invalid", False),
        ("my-module", False),
        ("module", False),
        ("always", False),
    ]
    
    passed = 0
    
    for name, should_pass in test_cases:
        try:
            result = sanitizer.sanitize_module_name(name)
            if should_pass:
                print(f"  ✓ Accepted: {name}")
                passed += 1
            else:
                print(f"  ✗ Should have rejected: {name}")
        except ValueError:
            if not should_pass:
                print(f"  ✓ Correctly rejected: {name}")
                passed += 1
            else:
                print(f"  ✗ Should have accepted: {name}")
    
    print(f"\nPassed: {passed}/{len(test_cases)}")
    
    return passed == len(test_cases)


def test_path_traversal_prevention():
    """Test path traversal prevention."""
    print("\n" + "=" * 70)
    print("TEST 3: PATH TRAVERSAL PREVENTION")
    print("=" * 70)
    
    sanitizer = InputSanitizer()
    
    dangerous_paths = [
        "../../etc/passwd",
        "../../../windows/system32",
        "/etc/passwd",
        "C:\\Windows\\System32",
    ]
    
    passed = 0
    
    for path in dangerous_paths:
        try:
            sanitizer.sanitize_file_path(path, base_dir="./outputs")
            print(f"  ✗ Should have rejected: {path}")
        except ValueError:
            print(f"  ✓ Correctly rejected: {path}")
            passed += 1
    
    print(f"\nPassed: {passed}/{len(dangerous_paths)}")
    
    return passed == len(dangerous_paths)


def test_security_audit():
    """Test security audit."""
    print("\n" + "=" * 70)
    print("TEST 4: SECURITY AUDIT")
    print("=" * 70)
    
    auditor = SecurityAuditor()
    results = auditor.run_security_audit()
    
    checks_completed = len(results['checks'])
    print(f"\nChecks completed: {checks_completed}")
    
    return checks_completed >= 7


def main():
    """Run all security tests."""
    print("\n" + "=" * 70)
    print("SECURITY TEST SUITE")
    print("=" * 70)
    
    results = []
    
    results.append(("Input Sanitization", test_input_sanitization()))
    results.append(("Module Name Validation", test_module_name_validation()))
    results.append(("Path Traversal Prevention", test_path_traversal_prevention()))
    results.append(("Security Audit", test_security_audit()))
    
    print("\n" + "=" * 70)
    print("SECURITY TEST SUMMARY")
    print("=" * 70)
    
    for name, passed in results:
        status = "✓ PASS" if passed else "✗ FAIL"
        print(f"{status} - {name}")
    
    passed_count = sum(1 for _, passed in results if passed)
    print(f"\nPassed: {passed_count}/{len(results)}")
    
    if passed_count == len(results):
        print("\n🔒 ALL SECURITY TESTS PASSED! 🔒")
    
    print("=" * 70)


if __name__ == "__main__":
    main()
