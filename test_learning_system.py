"""
Test Learning System

Tests error tracking and learning capabilities.

Usage: python test_learning_system.py
"""

import time
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))
from python.rtl_generator import RTLGenerator


def test_learning_system():
    """Test complete learning system."""
    print("=" * 70)
    print("TESTING LEARNING SYSTEM")
    print("=" * 70)
    
    # Create generator with learning enabled
    generator = RTLGenerator(
        use_mock=True,
        enable_verification=True,
        enable_learning=True
    )
    
    # Test cases with intentionally problematic descriptions
    test_cases = [
        # Good case
        "8-bit adder with carry input and output",
        
        # Potentially problematic cases
        "counter",  # Ambiguous
        "make a thing that adds",  # Vague
        "32-bit ALU with all operations",  # Complex
        "FSM for traffic light",  # Good
    ]
    
    print("\nTesting with learning enabled...")
    print(f"Test cases: {len(test_cases)}\n")
    
    results = []
    for i, description in enumerate(test_cases, 1):
        print(f"\n[{i}/{len(test_cases)}] Testing: {description}")
        print("-" * 70)
        
        result = generator.generate_with_learning(
            description=description,
            max_retries=3,
            verify=True
        )
        
        results.append(result)
        
        status = "✓ SUCCESS" if result.get('success', False) else "✗ FAILED"
        print(f"Result: {status}")
        
        if 'learning_info' in result:
            info = result['learning_info']
            print(f"Attempts: {info.get('attempts', 0)}")
            print(f"Errors encountered: {len(info.get('errors_encountered', []))}")
            
            if info.get('improvements_applied'):
                print("Improvements applied:")
                for improvement in info['improvements_applied']:
                    print(f"  - {improvement}")
        
        time.sleep(0.5)  # Rate limiting
    
    # Print summary
    print("\n" + "=" * 70)
    print("TEST SUMMARY")
    print("=" * 70)
    
    success_count = sum(1 for r in results if r.get('success', False))
    print(f"Successful: {success_count}/{len(test_cases)}")
    print(f"Failed: {len(test_cases) - success_count}/{len(test_cases)}")
    
    # Print learning statistics
    print("\n" + "=" * 70)
    print("LEARNING STATISTICS")
    print("=" * 70)
    
    generator.print_learning_report()
    
    print("\n" + "=" * 70)
    print("TEST COMPLETE")
    print("=" * 70)
    
    return results


if __name__ == "__main__":
    results = test_learning_system()
    
    print("\n✓ Learning system test complete")
