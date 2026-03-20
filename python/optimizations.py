"""
Performance Optimizations

Implementation of performance optimizations for RTL-Gen AI.

Usage:
    from python.optimizations import OptimizedCache, OptimizedPromptBuilder
"""

import hashlib
import time
from typing import Dict, Optional, Any
from pathlib import Path


class OptimizedCache:
    """Optimized caching system with LRU eviction."""
    
    def __init__(self, max_size: int = 1000, ttl_seconds: int = 3600):
        """Initialize optimized cache."""
        self.max_size = max_size
        self.ttl_seconds = ttl_seconds
        self.cache = {}
        self.access_times = {}
        self.access_counts = {}
    
    def _generate_key(self, *args, **kwargs) -> str:
        """Generate cache key from arguments."""
        key_data = str(args) + str(sorted(kwargs.items()))
        return hashlib.sha256(key_data.encode()).hexdigest()
    
    def get(self, key: str) -> Optional[Any]:
        """Get value from cache."""
        if key not in self.cache:
            return None
        
        # Check TTL
        age = time.time() - self.access_times.get(key, 0)
        if age > self.ttl_seconds:
            self._evict(key)
            return None
        
        # Update access tracking
        self.access_times[key] = time.time()
        self.access_counts[key] = self.access_counts.get(key, 0) + 1
        
        return self.cache[key]
    
    def set(self, key: str, value: Any):
        """Set value in cache."""
        if len(self.cache) >= self.max_size:
            self._evict_lru()
        
        self.cache[key] = value
        self.access_times[key] = time.time()
        self.access_counts[key] = 1
    
    def _evict(self, key: str):
        """Evict specific key."""
        if key in self.cache:
            del self.cache[key]
            del self.access_times[key]
            del self.access_counts[key]
    
    def _evict_lru(self):
        """Evict least recently used entry."""
        if not self.cache:
            return
        
        lru_key = min(self.access_times.keys(), key=lambda k: self.access_times[k])
        self._evict(lru_key)
    
    def clear(self):
        """Clear entire cache."""
        self.cache.clear()
        self.access_times.clear()
        self.access_counts.clear()
    
    def get_stats(self) -> Dict:
        """Get cache statistics."""
        return {
            'size': len(self.cache),
            'max_size': self.max_size,
            'utilization': len(self.cache) / self.max_size * 100,
            'total_accesses': sum(self.access_counts.values()),
        }


class OptimizedPromptBuilder:
    """Optimized prompt building with caching."""
    
    def __init__(self):
        """Initialize optimized prompt builder."""
        self.cache = OptimizedCache(max_size=500)
        self.template_cache = {}
    
    def build_prompt(self, description: str, context: Optional[Dict] = None) -> str:
        """Build prompt with caching."""
        cache_key = self.cache._generate_key(description, context)
        
        cached = self.cache.get(cache_key)
        if cached:
            return cached
        
        prompt = self._construct_prompt(description, context)
        self.cache.set(cache_key, prompt)
        
        return prompt
    
    def _construct_prompt(self, description: str, context: Optional[Dict]) -> str:
        """Construct prompt."""
        template = self._get_template()
        
        prompt = template.format(
            description=description,
            context=context or {}
        )
        
        return prompt
    
    def _get_template(self) -> str:
        """Get prompt template (cached)."""
        if 'base_template' not in self.template_cache:
            self.template_cache['base_template'] = """
Generate Verilog code for: {description}

Requirements:
- Syntactically correct Verilog
- Well-commented
- Best practices
"""
        
        return self.template_cache['base_template']


class BatchProcessor:
    """Batch processing for improved throughput."""
    
    def __init__(self, batch_size: int = 10):
        """Initialize batch processor."""
        self.batch_size = batch_size
        self.pending_requests = []
    
    def add_request(self, request: Dict):
        """Add request to batch."""
        self.pending_requests.append(request)
    
    def should_process(self) -> bool:
        """Check if batch should be processed."""
        return len(self.pending_requests) >= self.batch_size
    
    def process_batch(self) -> list:
        """Process current batch."""
        if not self.pending_requests:
            return []
        
        batch = self.pending_requests[:self.batch_size]
        self.pending_requests = self.pending_requests[self.batch_size:]
        
        results = []
        for request in batch:
            result = self._process_single(request)
            results.append(result)
        
        return results
    
    def _process_single(self, request: Dict) -> Dict:
        """Process single request."""
        return {'status': 'success', 'request': request}
    
    def flush(self) -> list:
        """Process all pending requests."""
        results = []
        while self.pending_requests:
            results.extend(self.process_batch())
        return results


if __name__ == "__main__":
    print("Optimizations Self-Test\n")
    
    # Test optimized cache
    print("Test 1: Optimized Cache")
    cache = OptimizedCache(max_size=5)
    
    for i in range(7):
        cache.set(f"key_{i}", f"value_{i}")
    
    stats = cache.get_stats()
    print(f"  Cache size: {stats['size']}/{stats['max_size']}")
    
    # Test cache hit
    value = cache.get("key_6")
    print(f"  Cache hit: {value}")
    
    # Test optimized prompt builder
    print("\nTest 2: Optimized Prompt Builder")
    builder = OptimizedPromptBuilder()
    
    prompt1 = builder.build_prompt("8-bit adder")
    prompt2 = builder.build_prompt("8-bit adder")
    
    print(f"  Prompts match: {prompt1 == prompt2}")
    
    # Test batch processor
    print("\nTest 3: Batch Processor")
    processor = BatchProcessor(batch_size=3)
    
    for i in range(5):
        processor.add_request({'id': i})
    
    results = processor.flush()
    print(f"  Processed {len(results)} requests")
    
    print("\n✓ Self-test complete")
