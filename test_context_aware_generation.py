"""
Test Context-Aware Generation

Tests conversation memory, user preferences, and context-aware generation.

Usage: python test_context_aware_generation.py
"""

import time
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

from python.user_preferences import UserPreferences


def test_user_preferences():
    """Test user preferences."""
    print("=" * 70)
    print("TEST 1: USER PREFERENCES")
    print("=" * 70)
    
    prefs = UserPreferences()
    test_user = "test_user_002"
    
    # Test default preferences
    print("\nDefault preferences:")
    coding_style = prefs.get_preference(test_user, 'coding_style')
    indentation = prefs.get_preference(test_user, 'indentation')
    print(f"  Coding style: {coding_style}")
    print(f"  Indentation: {indentation} spaces")
    
    # Update preferences
    print("\nUpdating preferences...")
    prefs.update_preferences(test_user, {
        'coding_style': 'verbose',
        'indentation': 4,
        'comment_density': 'high',
        'verification_level': 'full',
    })
    
    print("Updated preferences:")
    updated_prefs = prefs.get_all_preferences(test_user)
    for key in ['coding_style', 'indentation', 'comment_density', 'verification_level']:
        print(f"  {key}: {updated_prefs[key]}")
    
    # Test generation config
    print("\nGeneration config:")
    config = prefs.get_generation_config(test_user)
    for key, value in config.items():
        print(f"  {key}: {value}")
    
    print("\n✓ User preferences test complete\n")


def main():
    """Run all tests."""
    print("\n" + "=" * 70)
    print("CONTEXT-AWARE GENERATION - TESTS")
    print("=" * 70)
    
    start_time = time.time()
    
    # Test 1: User Preferences
    test_user_preferences()
    
    # Summary
    duration = time.time() - start_time
    
    print("=" * 70)
    print("TESTS COMPLETE")
    print("=" * 70)
    print(f"Total duration: {duration:.1f}s")
    print("=" * 70)


if __name__ == "__main__":
    main()
