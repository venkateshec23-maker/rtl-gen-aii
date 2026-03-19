"""
Batch Processor for RTL-Gen AI
Efficiently process multiple designs in parallel.

Usage:
    processor = BatchProcessor()
    results = processor.process_batch(descriptions)
"""

from typing import List, Dict
from concurrent.futures import ThreadPoolExecutor, as_completed
from python.rtl_generator import RTLGenerator
from python.performance_monitor import PerformanceMonitor


class BatchProcessor:
    """
    Process multiple designs efficiently.
    
    Features:
    - Parallel processing
    - Progress tracking
    - Error handling per design
    - Performance monitoring
    """
    
    def __init__(self, max_workers: int = 4, use_mock: bool = False):
        """
        Initialize batch processor.
        
        Args:
            max_workers: Number of parallel workers
            use_mock: Use mock LLM
        """
        self.max_workers = max_workers
        self.use_mock = use_mock
        self.monitor = PerformanceMonitor()
    
    def process_batch(self, descriptions: List[str]) -> List[Dict]:
        """
        Process multiple descriptions in parallel.
        
        Args:
            descriptions: List of design descriptions
            
        Returns:
            list: Results for each design
        """
        print(f"Processing {len(descriptions)} designs with {self.max_workers} workers...")
        
        results = []
        
        with self.monitor.measure("batch_processing"):
            with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
                # Submit all tasks
                futures = {
                    executor.submit(self._process_single, desc, i): (desc, i)
                    for i, desc in enumerate(descriptions)
                }
                
                # Collect results as they complete
                for future in as_completed(futures):
                    desc, idx = futures[future]
                    try:
                        result = future.result()
                        results.append((idx, result))
                        
                        status = "✓" if result['success'] else "✗"
                        print(f"  [{idx+1}/{len(descriptions)}] {status} {desc}")
                    
                    except Exception as e:
                        print(f"  [{idx+1}/{len(descriptions)}] ✗ {desc} - Exception: {e}")
                        results.append((idx, {'success': False, 'error': str(e)}))
        
        # Sort by original index
        results.sort(key=lambda x: x[0])
        
        return [r[1] for r in results]
    
    def _process_single(self, description: str, index: int) -> Dict:
        """Process single design."""
        generator = RTLGenerator(
            use_mock=self.use_mock,
            enable_verification=False,  # Disable for speed
            enable_monitoring=False,     # Disable per-design monitoring
        )
        
        return generator.generate(description)
    
    def get_performance_report(self) -> Dict:
        """Get performance report."""
        return self.monitor.get_report()


# ============================================================================
# SELF-TEST
# ============================================================================

if __name__ == "__main__":
    print("Batch Processor Self-Test\n")
    
    processor = BatchProcessor(max_workers=2, use_mock=True)
    
    descriptions = [
        "4-bit adder",
        "8-bit counter",
        "4-to-1 multiplexer",
        "8-bit register",
    ]
    
    results = processor.process_batch(descriptions)
    
    print("\n" + "=" * 70)
    print("RESULTS")
    print("=" * 70)
    
    success = sum(1 for r in results if r['success'])
    print(f"Success: {success}/{len(results)}")
    
    processor.monitor.print_report()
