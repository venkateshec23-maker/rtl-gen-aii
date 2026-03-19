"""
Cache Warming Script
Pre-generate common designs to populate cache.

Usage: python scripts/warm_cache.py
"""

from python.rtl_generator import RTLGenerator
from pathlib import Path


def warm_cache():
    """Pre-generate common designs."""
    
    print("=" * 70)
    print("CACHE WARMING - Pre-generating Common Designs")
    print("=" * 70)
    
    # Common designs to cache
    common_designs = [
        # Adders
        "4-bit adder",
        "8-bit adder",
        "16-bit adder",
        "4-bit adder with carry",
        "8-bit adder with carry",
        
        # Counters
        "4-bit counter",
        "8-bit counter",
        "4-bit counter with reset",
        "8-bit counter with reset and enable",
        "16-bit counter with load",
        
        # Multiplexers
        "2-to-1 multiplexer",
        "4-to-1 multiplexer",
        "8-to-1 multiplexer",
        "4-to-1 mux 8-bit",
        
        # Registers
        "4-bit register",
        "8-bit register",
        "16-bit register with enable",
        "8-bit shift register",
        
        # ALUs
        "4-bit ALU",
        "8-bit ALU",
        
        # Other common
        "D flip-flop",
        "4-bit comparator",
        "8-bit decoder",
        "Priority encoder",
    ]
    
    generator = RTLGenerator(use_mock=True, enable_verification=False)
    
    success_count = 0
    fail_count = 0
    
    for i, design in enumerate(common_designs, 1):
        print(f"\n[{i}/{len(common_designs)}] Generating: {design}")
        
        try:
            result = generator.generate(design)
            
            if result['success']:
                print(f"  ✓ Success - cached")
                success_count += 1
            else:
                print(f"  ✗ Failed: {result.get('message', 'Unknown error')}")
                fail_count += 1
        
        except Exception as e:
            print(f"  ✗ Exception: {e}")
            fail_count += 1
    
    print("\n" + "=" * 70)
    print("CACHE WARMING COMPLETE")
    print("=" * 70)
    print(f"Success: {success_count}")
    print(f"Failed: {fail_count}")
    print(f"Total: {len(common_designs)}")
    
    # Show cache stats
    from python.cache_manager import CacheManager
    cache = CacheManager()
    cache.print_stats()


if __name__ == "__main__":
    warm_cache()
