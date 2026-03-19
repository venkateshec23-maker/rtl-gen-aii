"""
Integration Test Suite
Tests complete workflows and component interactions.

Run with: pytest tests/test_integration.py -v
"""

import pytest
from pathlib import Path
import tempfile

from python.rtl_generator import RTLGenerator
from python.batch_processor import BatchProcessor


class TestEndToEndWorkflow:
    """Test complete end-to-end workflows."""
    
    def test_simple_generation_workflow(self):
        """Test: Simple generation from description to verified code."""
        generator = RTLGenerator(use_mock=True, enable_verification=True)
        
        result = generator.generate("4-bit adder with carry")
        
        assert result['success'] is True
        assert result['module_name'] is not None
        assert len(result['rtl_code']) > 0
        assert len(result['testbench_code']) > 0
        assert result['verification'] is not None
    
    def test_multiple_designs(self):
        """Test: Generate multiple different designs."""
        generator = RTLGenerator(use_mock=True, enable_verification=False)
        
        designs = [
            "4-bit adder",
            "8-bit counter",
            "4-to-1 multiplexer",
        ]
        
        results = []
        for desc in designs:
            result = generator.generate(desc)
            results.append(result)
        
        # All should succeed
        assert all(r['success'] for r in results)
        
        # All should have unique module names
        names = [r['module_name'] for r in results]
        assert len(names) == len(set(names))
    
    def test_cache_effectiveness(self):
        """Test: Cache improves performance."""
        generator = RTLGenerator(use_mock=True, enable_monitoring=True)
        
        # First generation
        result1 = generator.generate("8-bit adder")
        
        # Second generation (should be cached)
        result2 = generator.generate("8-bit adder")
        
        assert result1['success'] is True
        assert result2['success'] is True
        
        # Check cache stats
        stats = generator.get_stats()
        
        if 'cache_hits' in stats['llm_stats']:
            assert stats['llm_stats']['cache_hits'] >= 1
        elif hasattr(generator, 'client') and hasattr(generator.client, 'cache'):
            assert generator.client.cache.hits >= 1


class TestErrorHandling:
    """Test error handling scenarios."""
    
    def test_empty_description(self):
        """Test: Handle empty description gracefully."""
        generator = RTLGenerator(use_mock=True)
        
        result = generator.generate("")
        
        assert result['success'] is False
        assert 'error' in result or 'message' in result
    
    def test_invalid_description(self):
        """Test: Handle gibberish input."""
        generator = RTLGenerator(use_mock=True)
        
        result = generator.generate("asdfasdf qwerty")
        
        # Should either fail gracefully or generate something
        assert 'success' in result
    
    def test_verification_failure_handling(self):
        """Test: Handle verification failures gracefully."""
        generator = RTLGenerator(use_mock=True, enable_verification=True)
        
        # Try to generate something that might fail verification
        result = generator.generate("complex undefined circuit")
        
        # Should complete without crashing
        assert 'success' in result


class TestBatchProcessing:
    """Test batch processing functionality."""
    
    def test_batch_processing(self):
        """Test: Batch process multiple designs."""
        processor = BatchProcessor(max_workers=2, use_mock=True)
        
        designs = [
            "4-bit adder",
            "8-bit counter",
            "4-to-1 mux",
        ]
        
        results = processor.process_batch(designs)
        
        assert len(results) == len(designs)
        
        # Count successes
        successes = sum(1 for r in results if r.get('success'))
        assert successes >= len(designs) // 2  # At least half should succeed
    
    def test_batch_with_errors(self):
        """Test: Batch processing handles errors gracefully."""
        processor = BatchProcessor(max_workers=2, use_mock=True)
        
        designs = [
            "4-bit adder",
            "",  # Invalid
            "8-bit counter",
        ]
        
        results = processor.process_batch(designs)
        
        # Should complete without crashing
        assert len(results) == len(designs)


class TestFileOperations:
    """Test file I/O operations."""
    
    def test_output_files_created(self):
        """Test: Output files are created correctly."""
        generator = RTLGenerator(use_mock=True, enable_verification=False)
        
        result = generator.generate("4-bit adder")
        
        assert result['success'] is True
        assert 'file_paths' in result
        
        # Check files exist
        if 'output_dir' in result['file_paths']:
            output_dir = Path(result['file_paths']['output_dir'])
            assert output_dir.exists()
    
    def test_file_cleanup(self):
        """Test: Temporary files are cleaned up."""
        from python.config import CACHE_DIR
        
        # Count temp files before
        temp_before = len(list(CACHE_DIR.glob("**/*.tmp")))
        
        generator = RTLGenerator(use_mock=True)
        generator.generate("4-bit adder")
        
        # Count temp files after
        temp_after = len(list(CACHE_DIR.glob("**/*.tmp")))
        
        # Should not accumulate temp files
        assert temp_after <= temp_before + 5  # Allow some temporary files


class TestPerformance:
    """Test performance requirements."""
    
    def test_generation_time(self):
        """Test: Generation completes within time limit."""
        import time
        
        generator = RTLGenerator(use_mock=True, enable_verification=False)
        
        start = time.time()
        result = generator.generate("8-bit adder")
        duration = time.time() - start
        
        assert result['success'] is True
        assert duration < 30.0  # Should complete in under 30 seconds
    
    def test_memory_usage(self):
        """Test: Memory usage is reasonable."""
        import psutil
        process = psutil.Process()
        
        mem_before = process.memory_info().rss / 1024 / 1024
        
        generator = RTLGenerator(use_mock=True, enable_verification=False)
        
        for i in range(5):
            generator.generate(f"{4*(i+1)}-bit adder")
        
        mem_after = process.memory_info().rss / 1024 / 1024
        mem_increase = mem_after - mem_before
        
        # Memory increase should be reasonable (< 500MB for 5 generations)
        assert mem_increase < 500


if __name__ == "__main__":
    pytest.main([__file__, '-v', '--tb=short'])
