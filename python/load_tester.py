"""
Load Tester

Performs load testing and stress testing on RTL-Gen AI.

Usage:
    from python.load_tester import LoadTester
    
    tester = LoadTester()
    results = tester.run_load_test(num_requests=50)
"""

import time
import threading
import queue
from pathlib import Path
from typing import Dict, List
from datetime import datetime
import json
import statistics


class LoadTester:
    """Load testing and stress testing."""
    
    def __init__(self):
        """Initialize load tester."""
        self.results = {
            'timestamp': datetime.now().isoformat(),
            'tests': [],
        }
        
        self.test_descriptions = [
            "4-bit adder",
            "8-bit counter with enable",
            "16-bit register",
            "8-bit ALU",
            "16-bit shift register",
            "4-bit multiplexer",
            "8-bit comparator",
            "16-bit adder",
            "8-bit priority encoder",
            "16-bit barrel shifter",
        ]
    
    def run_load_test(self, num_requests: int = 50, concurrent_users: int = 5, scenario_name: str = 'custom') -> Dict:
        """Run load test."""
        print("\n" + "=" * 70)
        print(f"LOAD TEST: {scenario_name.upper()}")
        print("=" * 70)
        print(f"Requests: {num_requests}")
        print(f"Concurrent users: {concurrent_users}\n")
        
        start_time = time.time()
        
        request_queue = queue.Queue()
        
        for i in range(num_requests):
            description = self.test_descriptions[i % len(self.test_descriptions)]
            request_queue.put({'id': i, 'description': description})
        
        results_lock = threading.Lock()
        request_results = []
        
        def worker():
            """Worker thread for processing requests."""
            from python.rtl_generator import RTLGenerator
            
            generator = RTLGenerator(use_mock=True)
            
            while True:
                try:
                    request = request_queue.get_nowait()
                except queue.Empty:
                    break
                
                request_start = time.time()
                
                try:
                    result = generator.generate(request['description'], verify=False)
                    success = result is not None
                    error = None
                except Exception as e:
                    success = False
                    error = str(e)
                
                request_end = time.time()
                
                with results_lock:
                    request_results.append({
                        'id': request['id'],
                        'success': success,
                        'duration_s': request_end - request_start,
                        'error': error,
                    })
                
                request_queue.task_done()
        
        threads = []
        for _ in range(concurrent_users):
            thread = threading.Thread(target=worker)
            thread.start()
            threads.append(thread)
        
        for thread in threads:
            thread.join()
        
        end_time = time.time()
        total_duration = end_time - start_time
        
        analysis = self._analyze_results(request_results, total_duration)
        
        test_result = {
            'scenario': scenario_name,
            'num_requests': num_requests,
            'concurrent_users': concurrent_users,
            'total_duration_s': total_duration,
            'analysis': analysis,
        }
        
        self.results['tests'].append(test_result)
        self._print_test_summary(test_result)
        
        return test_result
    
    def _analyze_results(self, request_results: List[Dict], total_duration: float) -> Dict:
        """Analyze load test results."""
        successful = [r for r in request_results if r['success']]
        failed = [r for r in request_results if not r['success']]
        
        durations = [r['duration_s'] for r in successful]
        
        analysis = {
            'total_requests': len(request_results),
            'successful': len(successful),
            'failed': len(failed),
            'success_rate': len(successful) / len(request_results) * 100 if request_results else 0,
            'throughput_req_per_s': len(request_results) / total_duration if total_duration > 0 else 0,
        }
        
        if durations:
            analysis.update({
                'avg_response_time_s': statistics.mean(durations),
                'min_response_time_s': min(durations),
                'max_response_time_s': max(durations),
                'median_response_time_s': statistics.median(durations),
                'stddev_response_time_s': statistics.stdev(durations) if len(durations) > 1 else 0,
            })
            
            sorted_durations = sorted(durations)
            analysis.update({
                'p50_response_time_s': sorted_durations[int(len(sorted_durations) * 0.50)],
                'p95_response_time_s': sorted_durations[int(len(sorted_durations) * 0.95)],
                'p99_response_time_s': sorted_durations[int(len(sorted_durations) * 0.99)],
            })
        
        return analysis
    
    def _print_test_summary(self, test_result: Dict):
        """Print test summary."""
        analysis = test_result['analysis']
        
        print(f"Results:")
        print(f"  Total: {analysis['total_requests']}")
        print(f"  Successful: {analysis['successful']}")
        print(f"  Failed: {analysis['failed']}")
        print(f"  Success rate: {analysis['success_rate']:.1f}%")
        
        print(f"\nPerformance:")
        print(f"  Total duration: {test_result['total_duration_s']:.2f}s")
        print(f"  Throughput: {analysis['throughput_req_per_s']:.2f} req/s")
        
        if 'avg_response_time_s' in analysis:
            print(f"  Avg response: {analysis['avg_response_time_s']:.3f}s")
            print(f"  Median: {analysis['median_response_time_s']:.3f}s")
            print(f"  95th percentile: {analysis['p95_response_time_s']:.3f}s")
    
    def save_results(self, output_file: str = None):
        """Save load test results."""
        if output_file is None:
            output_file = f"load_test_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        with open(output_file, 'w') as f:
            json.dump(self.results, f, indent=2)
        
        print(f"\n✓ Results saved: {output_file}")


if __name__ == "__main__":
    print("Load Tester Self-Test\n")
    
    tester = LoadTester()
    result = tester.run_load_test(num_requests=10, concurrent_users=2, scenario_name='Light')
    tester.save_results()
    print("\n✓ Self-test complete")
