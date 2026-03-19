"""
Performance Testing Script
Measures system performance under various loads.

Usage: python test_performance.py
"""

import time
from python.rtl_generator import RTLGenerator
from python.batch_processor import BatchProcessor
from python.cache_manager import CacheManager


def test_cache_performance():
    """Test cache hit/miss performance."""
    print("=" * 70)
    print("CACHE PERFORMANCE TEST")
    print("=" * 70)
    
    generator = RTLGenerator(use_mock=True)
    
    # First generation (cache miss)
    print("\n1. First generation (cache miss):")
    start = time.time()
    result1 = generator.generate("8-bit adder")
    time1 = time.time() - start
    print(f"   Time: {time1:.3f}s")
    
    # Second generation (cache hit)
    print("\n2. Second generation (cache hit):")
    start = time.time()
    result2 = generator.generate("8-bit adder")
    time2 = time.time() - start
    print(f"   Time: {time2:.3f}s")
    
    speedup = time1 / time2 if time2 > 0 else 0
    print(f"\n   Speedup: {speedup:.1f}x faster with cache")
    
    # Show cache stats
    cache = CacheManager()
    cache.print_stats()


def test_batch_performance():
    """Test batch processing performance."""
    print("\n" + "=" * 70)
    print("BATCH PROCESSING TEST")
    print("=" * 70)
    
    designs = [
        "4-bit adder",
        "8-bit counter",
        "4-to-1 mux",
        "8-bit register",
        "D flip-flop",
    ]
    
    # Sequential processing
    print("\n1. Sequential processing:")
    generator = RTLGenerator(use_mock=True, enable_verification=False)
    
    start = time.time()
    for design in designs:
        generator.generate(design)
    sequential_time = time.time() - start
    print(f"   Time: {sequential_time:.3f}s")
    
    # Batch processing
    print("\n2. Batch processing (parallel):")
    processor = BatchProcessor(max_workers=4, use_mock=True)
    
    start = time.time()
    processor.process_batch(designs)
    batch_time = time.time() - start
    print(f"   Time: {batch_time:.3f}s")
    
    speedup = sequential_time / batch_time if batch_time > 0 else 0
    print(f"\n   Speedup: {speedup:.1f}x faster with parallel processing")


def test_memory_usage():
    """Test memory usage."""
    print("\n" + "=" * 70)
    print("MEMORY USAGE TEST")
    print("=" * 70)
    
    import psutil
    process = psutil.Process()
    
    # Initial memory
    mem_before = process.memory_info().rss / 1024 / 1024
    print(f"\n1. Initial memory: {mem_before:.2f} MB")
    
    # Generate multiple designs
    generator = RTLGenerator(use_mock=True, enable_verification=False)
    
    for i in range(10):
        generator.generate(f"{4*(i+1)}-bit adder")
    
    # Final memory
    mem_after = process.memory_info().rss / 1024 / 1024
    print(f"2. After 10 generations: {mem_after:.2f} MB")
    print(f"3. Memory increase: {mem_after - mem_before:.2f} MB")


if __name__ == "__main__":
    print("\n")
    print("*" * 70)
    print("PERFORMANCE TEST SUITE")
    print("*" * 70)
    
    test_cache_performance()
    test_batch_performance()
    test_memory_usage()
    
    print("\n" + "*" * 70)
    print("ALL TESTS COMPLETE")
    print("*" * 70)
