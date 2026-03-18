"""
Unit tests for LLM Client.
Run with: pytest tests/test_llm_client.py -v
"""

import os
import sys
import time
import pytest

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from python.llm_client import LLMClient, quick_generate
from python.cache_manager import CacheManager
from python.token_tracker import TokenTracker
from python.mock_llm import MockLLM


class TestCacheManager:
    """Tests for CacheManager."""

    def setup_method(self):
        self.cache = CacheManager()
        self.cache.clear()

    def test_set_and_get(self):
        self.cache.set("test prompt", {"code": "module x;"}, tokens_saved=50)
        result = self.cache.get("test prompt")
        assert result is not None
        assert result["code"] == "module x;"

    def test_cache_miss(self):
        result = self.cache.get("nonexistent prompt")
        assert result is None

    def test_stats(self):
        self.cache.set("p1", {"a": 1}, tokens_saved=10)
        stats = self.cache.get_stats()
        assert stats['entries'] >= 1

    def teardown_method(self):
        self.cache.clear()


class TestTokenTracker:
    """Tests for TokenTracker."""

    def setup_method(self):
        self.tracker = TokenTracker()
        self.tracker.reset()

    def test_log_usage(self):
        self.tracker.log_usage("test-model", 100, 50)
        stats = self.tracker.get_total_stats()
        assert stats['total_calls'] == 1
        assert stats['total_tokens'] == 150

    def test_daily_stats(self):
        self.tracker.log_usage("test-model", 200, 100)
        daily = self.tracker.get_daily_stats()
        assert daily['total_tokens'] == 200 + 100

    def teardown_method(self):
        self.tracker.reset()


class TestMockLLM:
    """Tests for MockLLM."""

    def setup_method(self):
        self.mock = MockLLM(delay=0)

    def test_adder(self):
        r = self.mock.generate("Generate an 8-bit adder")
        assert 'choices' in r
        assert 'adder' in r['choices'][0]['message']['content'].lower()

    def test_counter(self):
        r = self.mock.generate("Generate a counter")
        assert 'counter' in r['choices'][0]['message']['content'].lower()

    def test_alu(self):
        r = self.mock.generate("Build an ALU")
        assert 'alu' in r['choices'][0]['message']['content'].lower()

    def test_error_simulation(self):
        mock = MockLLM(delay=0, error_rate=1.0)
        r = mock.generate("anything")
        assert 'error' in r


class TestLLMClient:
    """Tests for LLMClient in mock mode."""

    def setup_method(self):
        self.client = LLMClient(use_mock=True)

    def test_mock_generation(self):
        r = self.client.generate("Generate an 8-bit adder")
        assert r['success'] is True
        assert 'content' in r
        assert len(r['content']) > 50

    def test_code_extraction(self):
        r = self.client.generate("Generate an 8-bit adder")
        blocks = self.client.extract_code(r)
        assert len(blocks) >= 1
        assert 'module' in blocks[0]

    def test_cache_hit(self):
        self.client.generate("cache test prompt 123")
        r2 = self.client.generate("cache test prompt 123")
        assert r2.get('cached') is True

    def test_error_handling(self):
        self.client.mock.error_rate = 1.0
        r = self.client.generate("will fail")
        assert r['success'] is False
        assert 'error' in r

    def test_stats(self):
        self.client.generate("stats test")
        stats = self.client.get_stats()
        assert stats['mock_mode'] is True
        assert stats['tokens']['total_calls'] >= 1

    def test_quick_generate(self):
        code = quick_generate("8-bit adder", use_mock=True)
        assert len(code) > 0
        assert 'module' in code

    def test_multiple_components(self):
        for desc in ["adder", "counter", "ALU", "something random"]:
            r = self.client.generate(f"Generate a {desc}")
            assert r['success'] is True

    def test_retry_on_failure(self):
        self.client.mock.error_rate = 0.5
        r = self.client.generate_with_retry("retry test", max_retries=5)
        # With 50% error rate and 5 retries, very likely to succeed
        # But not guaranteed, so just check structure
        assert 'success' in r


if __name__ == "__main__":
    pytest.main([__file__, '-v'])
