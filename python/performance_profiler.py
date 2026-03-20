"""
Performance Profiler

Profiles performance and identifies bottlenecks.

Usage:
    from python.performance_profiler import PerformanceProfiler
    
    profiler = PerformanceProfiler()
    with profiler.profile('generation'):
        # Code to profile
        pass
"""

import time
from pathlib import Path
from typing import Dict, Optional, Callable
from datetime import datetime
from contextlib import contextmanager
import json
import statistics


class PerformanceProfiler:
    """Performance profiling and analysis."""
    
    def __init__(self):
        """Initialize performance profiler."""
        self.timings = {}
        self.profiling_data = {}
    
    @contextmanager
    def profile(self, operation_name: str):
        """Context manager for profiling code block."""
        start_time = time.time()
        start_cpu = time.process_time()
        
        yield
        
        end_time = time.time()
        end_cpu = time.process_time()
        
        if operation_name not in self.timings:
            self.timings[operation_name] = []
        
        self.timings[operation_name].append({
            'wall_time_s': end_time - start_time,
            'cpu_time_s': end_cpu - start_cpu,
            'timestamp': datetime.now().isoformat(),
        })
    
    def get_timing_stats(self, operation_name: str) -> Optional[Dict]:
        """Get timing statistics for an operation."""
        if operation_name not in self.timings:
            return None
        
        timings = self.timings[operation_name]
        wall_times = [t['wall_time_s'] for t in timings]
        cpu_times = [t['cpu_time_s'] for t in timings]
        
        return {
            'operation': operation_name,
            'count': len(timings),
            'wall_time': {
                'mean': statistics.mean(wall_times),
                'median': statistics.median(wall_times),
                'min': min(wall_times),
                'max': max(wall_times),
                'stdev': statistics.stdev(wall_times) if len(wall_times) > 1 else 0,
            },
            'cpu_time': {
                'mean': statistics.mean(cpu_times),
                'median': statistics.median(cpu_times),
                'min': min(cpu_times),
                'max': max(cpu_times),
                'stdev': statistics.stdev(cpu_times) if len(cpu_times) > 1 else 0,
            },
        }
    
    def print_timing_report(self):
        """Print timing report for all operations."""
        print("\n" + "=" * 70)
        print("PERFORMANCE TIMING REPORT")
        print("=" * 70)
        
        for operation_name in sorted(self.timings.keys()):
            stats = self.get_timing_stats(operation_name)
            
            print(f"\n{operation_name}:")
            print(f"  Count: {stats['count']}")
            print(f"  Avg wall time: {stats['wall_time']['mean']:.3f}s")
            print(f"  Avg CPU time: {stats['cpu_time']['mean']:.3f}s")
    
    def identify_bottlenecks(self) -> list:
        """Identify performance bottlenecks."""
        bottlenecks = []
        
        for operation_name in self.timings.keys():
            stats = self.get_timing_stats(operation_name)
            
            if stats['wall_time']['mean'] > 1.0:
                bottlenecks.append({
                    'operation': operation_name,
                    'avg_time_s': stats['wall_time']['mean'],
                    'severity': 'high' if stats['wall_time']['mean'] > 5.0 else 'medium',
                })
        
        return bottlenecks
    
    def generate_report(self, output_file: Optional[str] = None) -> str:
        """Generate comprehensive performance report."""
        if output_file is None:
            output_file = f"performance_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
        
        report = f"""# Performance Profile Report

**Generated:** {datetime.now().isoformat()}

---

## Timing Summary

"""
        
        for operation_name in sorted(self.timings.keys()):
            stats = self.get_timing_stats(operation_name)
            
            report += f"\n### {operation_name}\n\n"
            report += f"- **Executions:** {stats['count']}\n"
            report += f"- **Avg wall time:** {stats['wall_time']['mean']:.3f}s\n"
            report += f"- **Median:** {stats['wall_time']['median']:.3f}s\n"
            report += f"- **Min/Max:** {stats['wall_time']['min']:.3f}s / {stats['wall_time']['max']:.3f}s\n"
            report += f"- **Std dev:** {stats['wall_time']['stdev']:.3f}s\n"
        
        # Bottlenecks
        bottlenecks = self.identify_bottlenecks()
        
        if bottlenecks:
            report += "\n---\n\n## Identified Bottlenecks\n\n"
            for i, bottleneck in enumerate(bottlenecks, 1):
                report += f"{i}. {bottleneck['operation']}: {bottleneck['avg_time_s']:.3f}s [{bottleneck['severity']}]\n"
        else:
            report += "\n---\n\n## Identified Bottlenecks\n\n*No significant bottlenecks identified*\n"
        
        report += "\n---\n\n*Performance profiling completed*\n"
        
        Path(output_file).write_text(report)
        print(f"\n✓ Performance report saved: {output_file}")
        
        return output_file


if __name__ == "__main__":
    print("Performance Profiler Self-Test\n")
    
    profiler = PerformanceProfiler()
    
    print("Profiling test operations...")
    
    for i in range(5):
        with profiler.profile('fast_operation'):
            time.sleep(0.05)
    
    for i in range(3):
        with profiler.profile('slow_operation'):
            time.sleep(0.2)
    
    profiler.print_timing_report()
    
    bottlenecks = profiler.identify_bottlenecks()
    print(f"\nBottlenecks identified: {len(bottlenecks)}")
    
    profiler.generate_report()
    
    print("\n✓ Self-test complete")
