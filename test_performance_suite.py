"""
Performance Test Suite

Tests load handling and performance optimizations.

Usage: python test_performance_suite.py
"""

import time
from python.load_tester import LoadTester
from python.performance_profiler import PerformanceProfiler
from python.optimizations import OptimizedCache, OptimizedPromptBuilder


def test_load_handling():
    """Test load handling capabilities."""
    print("=" * 70)
    print("TEST 1: LOAD HANDLING")
    print("=" * 70)
    
    tester = LoadTester()
    
    result = tester.run_load_test(
        num_requests=20,
        concurrent_users=4,
        scenario_name='Medium Load Test'
    )
    
    success = result['analysis']['success_rate'] >= 85
    
    if success:
        print(f"\n✓ Load test passed (success rate: {result['analysis']['success_rate']:.1f}%)")
    else:
        print(f"\n✗ Load test failed (success rate: {result['analysis']['success_rate']:.1f}%)")
    
    return success


def test_performance_profiling():
    """Test performance profiling."""
    print("\n" + "=" * 70)
    print("TEST 2: PERFORMANCE PROFILING")
    print("=" * 70)
    
    profiler = PerformanceProfiler()
    
    for i in range(10):
        with profiler.profile('test_operation'):
            time.sleep(0.02)
    
    stats = profiler.get_timing_stats('test_operation')
    
    print(f"\nOperation count: {stats['count']}")
    print(f"Average time: {stats['wall_time']['mean']:.3f}s")
    
    profiler.generate_report()
    
    return stats['count'] == 10


def test_caching():
    """Test caching optimization."""
    print("\n" + "=" * 70)
    print("TEST 3: CACHING OPTIMIZATION")
    print("=" * 70)
    
    cache = OptimizedCache(max_size=100)
    
    cache.set("key1", "value1")
    cache.set("key2", "value2")
    
    hit = cache.get("key1")
    miss = cache.get("key3")
    
    print(f"\nCache hit: {hit}")
    print(f"Cache miss: {miss}")
    
    stats = cache.get_stats()
    print(f"Cache stats: size={stats['size']}, utilization={stats['utilization']:.1f}%")
    
    return hit == "value1" and miss is None


def test_cache_performance():
    """Test cache performance improvement."""
    print("\n" + "=" * 70)
    print("TEST 4: CACHE PERFORMANCE IMPROVEMENT")
    print("=" * 70)
    
    builder = OptimizedPromptBuilder()
    
    start = time.time()
    prompt1 = builder.build_prompt("8-bit adder")
    time_without_cache = time.time() - start
    
    start = time.time()
    prompt2 = builder.build_prompt("8-bit adder")
    time_with_cache = time.time() - start
    
    speedup = time_without_cache / time_with_cache if time_with_cache > 0 else 1
    
    print(f"\nFirst call (no cache): {time_without_cache*1000:.3f}ms")
    print(f"Second call (cached): {time_with_cache*1000:.3f}ms")
    print(f"Speedup: {speedup:.1f}x")
    
    return speedup > 1


def test_concurrent_load():
    """Test concurrent request handling."""
    print("\n" + "=" * 70)
    print("TEST 5: CONCURRENT REQUEST HANDLING")
    print("=" * 70)
    
    tester = LoadTester()
    
    result = tester.run_load_test(
        num_requests=30,
        concurrent_users=6,
        scenario_name='Concurrent Test'
    )
    
    throughput = result['analysis']['throughput_req_per_s']
    
    print(f"\nThroughput: {throughput:.2f} req/s")
    print(f"Success rate: {result['analysis']['success_rate']:.1f}%")
    
    return result['analysis']['success_rate'] >= 80


def main():
    """Run all performance tests."""
    print("\n" + "=" * 70)
    print("PERFORMANCE TEST SUITE")
    print("=" * 70)
    
    results = []
    
    results.append(("Load Handling", test_load_handling()))
    results.append(("Performance Profiling", test_performance_profiling()))
    results.append(("Caching", test_caching()))
    results.append(("Cache Performance", test_cache_performance()))
    results.append(("Concurrent Load", test_concurrent_load()))
    
    print("\n" + "=" * 70)
    print("PERFORMANCE TEST SUMMARY")
    print("=" * 70)
    
    for name, passed in results:
        status = "✓ PASS" if passed else "✗ FAIL"
        print(f"{status} - {name}")
    
    passed_count = sum(1 for _, passed in results if passed)
    print(f"\nPassed: {passed_count}/{len(results)}")
    
    if passed_count == len(results):
        print("\n⚡ ALL PERFORMANCE TESTS PASSED! ⚡")
    
    print("=" * 70)


if __name__ == "__main__":
    main()
