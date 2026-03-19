"""
Performance Monitor for RTL-Gen AI
Tracks execution time, memory usage, and bottlenecks.

Usage:
    from python.performance_monitor import PerformanceMonitor
    
    monitor = PerformanceMonitor()
    
    with monitor.measure("code_generation"):
        # Your code here
        result = generate_code()
    
    monitor.print_report()
"""

import time
import psutil
from typing import Dict, Optional
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
import json


class PerformanceMonitor:
    """
    Monitor performance metrics.
    
    Tracks:
    - Execution time per component
    - Memory usage
    - API call counts
    - Cache hit rates
    """
    
    def __init__(self):
        """Initialize performance monitor."""
        self.metrics = {
            'timings': {},
            'memory': {},
            'counts': {},
            'start_time': datetime.now(),
        }
        
        self.process = psutil.Process()
    
    @contextmanager
    def measure(self, operation: str):
        """
        Context manager to measure operation time.
        
        Usage:
            with monitor.measure("parsing"):
                parse_input()
        """
        start_time = time.time()
        start_memory = self.process.memory_info().rss / 1024 / 1024  # MB
        
        try:
            yield
        finally:
            end_time = time.time()
            end_memory = self.process.memory_info().rss / 1024 / 1024
            
            duration = end_time - start_time
            memory_delta = end_memory - start_memory
            
            # Store timing
            if operation not in self.metrics['timings']:
                self.metrics['timings'][operation] = []
            self.metrics['timings'][operation].append(duration)
            
            # Store memory
            if operation not in self.metrics['memory']:
                self.metrics['memory'][operation] = []
            self.metrics['memory'][operation].append(memory_delta)
    
    def increment(self, counter: str, amount: int = 1):
        """Increment a counter."""
        if counter not in self.metrics['counts']:
            self.metrics['counts'][counter] = 0
        self.metrics['counts'][counter] += amount
    
    def get_report(self) -> Dict:
        """Get performance report."""
        report = {
            'total_runtime': (datetime.now() - self.metrics['start_time']).total_seconds(),
            'operations': {},
            'counters': self.metrics['counts'],
        }
        
        # Calculate statistics for each operation
        for operation, times in self.metrics['timings'].items():
            report['operations'][operation] = {
                'count': len(times),
                'total_time': sum(times),
                'avg_time': sum(times) / len(times) if times else 0,
                'min_time': min(times) if times else 0,
                'max_time': max(times) if times else 0,
            }
            
            # Add memory if available
            if operation in self.metrics['memory']:
                memories = self.metrics['memory'][operation]
                report['operations'][operation]['avg_memory_mb'] = sum(memories) / len(memories) if memories else 0
        
        return report
    
    def print_report(self):
        """Print formatted performance report."""
        report = self.get_report()
        
        print("\n" + "=" * 70)
        print("PERFORMANCE REPORT")
        print("=" * 70)
        
        print(f"\nTotal Runtime: {report['total_runtime']:.2f}s")
        
        print("\n" + "-" * 70)
        print("Operation Timings:")
        print("-" * 70)
        
        for op, stats in sorted(report['operations'].items(), 
                               key=lambda x: x[1]['total_time'], 
                               reverse=True):
            print(f"\n{op}:")
            print(f"  Count: {stats['count']}")
            print(f"  Total: {stats['total_time']:.3f}s")
            print(f"  Average: {stats['avg_time']:.3f}s")
            print(f"  Min: {stats['min_time']:.3f}s")
            print(f"  Max: {stats['max_time']:.3f}s")
            if 'avg_memory_mb' in stats:
                print(f"  Memory: {stats['avg_memory_mb']:.2f} MB")
        
        if report['counters']:
            print("\n" + "-" * 70)
            print("Counters:")
            print("-" * 70)
            for counter, value in report['counters'].items():
                print(f"  {counter}: {value}")
        
        print("\n" + "=" * 70)
    
    def save_report(self, filename: str = "performance_report.json"):
        """Save report to JSON file."""
        report = self.get_report()
        
        # Convert datetime to string
        report['timestamp'] = datetime.now().isoformat()
        
        with open(filename, 'w') as f:
            json.dump(report, f, indent=2)
        
        print(f"Performance report saved to: {filename}")


# Global monitor instance
monitor = PerformanceMonitor()


# ============================================================================
# SELF-TEST
# ============================================================================

if __name__ == "__main__":
    print("Performance Monitor Self-Test\n")
    
    monitor = PerformanceMonitor()
    
    # Test timing measurement
    with monitor.measure("test_operation_1"):
        time.sleep(0.1)
    
    with monitor.measure("test_operation_2"):
        time.sleep(0.2)
    
    # Multiple measurements
    for i in range(5):
        with monitor.measure("repeated_operation"):
            time.sleep(0.05)
    
    # Test counters
    monitor.increment("api_calls", 10)
    monitor.increment("cache_hits", 7)
    monitor.increment("cache_misses", 3)
    
    # Print report
    monitor.print_report()
    
    # Save report
    monitor.save_report("test_performance.json")
