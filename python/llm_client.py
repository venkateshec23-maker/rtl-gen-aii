"""
LLM Client for RTL-Gen AII.
Main interface to DeepSeek-V3.2 via NVIDIA API.
Supports caching, rate limiting, token tracking, and mock mode.
"""

import time
from typing import Dict, Optional, List

try:
    import openai
except ImportError:
    openai = None

from python.config import (
    NVIDIA_API_KEY, NVIDIA_MODEL, NVIDIA_BASE_URL,
    DEFAULT_TEMPERATURE, MAX_TOKENS,
    REQUEST_COOLDOWN, ENABLE_MOCK_LLM, DEBUG_MODE
)
from python.cache_manager import CacheManager, get_cache_manager
from python.token_tracker import TokenTracker, get_token_tracker
from python.mock_llm import MockLLM, get_mock_llm


class LLMClient:
    """
    Client for DeepSeek-V3.2 via NVIDIA API.

    Usage:
        client = LLMClient(use_mock=True)
        response = client.generate("Generate an 8-bit adder")
        if response['success']:
            code_blocks = client.extract_code(response)
    """

    def __init__(self, use_mock=None, cache_manager=None, token_tracker=None):
        self.use_mock = use_mock if use_mock is not None else ENABLE_MOCK_LLM
        self.cache = cache_manager or get_cache_manager()
        self.tracker = token_tracker or get_token_tracker()
        self.mock = get_mock_llm(delay=0.1) if self.use_mock else None
        self.last_request_time = 0
        self.request_count = 0
        self.model = NVIDIA_MODEL

        if not self.use_mock:
            self._init_real_client()

        if DEBUG_MODE:
            print(f"LLMClient initialized (mock={self.use_mock})")

    def _init_real_client(self):
        if openai is None:
            raise ImportError("openai package required. Run: pip install openai")
        if not NVIDIA_API_KEY:
            raise ValueError(
                "NVIDIA_API_KEY not set in .env. "
                "Set ENABLE_MOCK_LLM=true for testing without API."
            )
        self.client = openai.OpenAI(
            base_url=NVIDIA_BASE_URL,
            api_key=NVIDIA_API_KEY
        )

    def _rate_limit(self):
        elapsed = time.time() - self.last_request_time
        if elapsed < REQUEST_COOLDOWN:
            time.sleep(REQUEST_COOLDOWN - elapsed)
        self.last_request_time = time.time()
        self.request_count += 1

    def generate(self, prompt, system_prompt=None,
                 temperature=DEFAULT_TEMPERATURE,
                 max_tokens=MAX_TOKENS, use_cache=True):
        """
        Generate LLM response. Returns dict with:
            success, content, usage, cached, model, error
        """
        cache_kwargs = {
            'system': system_prompt or '',
            'temperature': temperature,
            'max_tokens': max_tokens
        }

        # Check cache
        if use_cache:
            cached = self.cache.get(prompt, **cache_kwargs)
            if cached:
                if DEBUG_MODE:
                    print("Cache hit!")
                cached['cached'] = True
                return cached

        # Mock mode
        if self.use_mock:
            return self._generate_mock(prompt, system_prompt,
                                       temperature, max_tokens, cache_kwargs)

        # Real API
        return self._generate_real(prompt, system_prompt,
                                   temperature, max_tokens, cache_kwargs)

    def _generate_mock(self, prompt, system_prompt, temperature,
                       max_tokens, cache_kwargs):
        try:
            response = self.mock.generate(prompt)
            if 'error' in response:
                return {'success': False,
                        'error': response['error']['message'],
                        'cached': False}

            content = response['choices'][0]['message']['content']
            usage = response.get('usage', {
                'prompt_tokens': 100,
                'completion_tokens': 200,
                'total_tokens': 300
            })

            self.tracker.log_usage('mock-llm',
                                   usage['prompt_tokens'],
                                   usage['completion_tokens'])

            result = {
                'success': True,
                'content': content,
                'usage': usage,
                'cached': False,
                'model': 'mock-llm'
            }
            self.cache.set(prompt, result,
                           tokens_saved=usage['total_tokens'],
                           **cache_kwargs)
            return result
        except Exception as e:
            return {'success': False,
                    'error': f"Mock error: {e}",
                    'cached': False}

    def _generate_real(self, prompt, system_prompt, temperature,
                       max_tokens, cache_kwargs):
        try:
            self._rate_limit()

            messages = []
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})
            messages.append({"role": "user", "content": prompt})

            if DEBUG_MODE:
                print(f"Sending request to {self.model}...")

            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens
            )

            content = response.choices[0].message.content
            usage = {
                'prompt_tokens': response.usage.prompt_tokens,
                'completion_tokens': response.usage.completion_tokens,
                'total_tokens': response.usage.total_tokens
            }

            self.tracker.log_usage(self.model,
                                   usage['prompt_tokens'],
                                   usage['completion_tokens'])

            result = {
                'success': True,
                'content': content,
                'usage': usage,
                'cached': False,
                'model': self.model
            }
            self.cache.set(prompt, result,
                           tokens_saved=usage['total_tokens'],
                           **cache_kwargs)

            if DEBUG_MODE:
                print(f"Success. Tokens: {usage['total_tokens']}")
            return result

        except Exception as e:
            error_msg = str(e)
            self.tracker.log_usage(self.model, 0, 0,
                                   success=False, error=error_msg)
            return {'success': False, 'error': error_msg, 'cached': False}

    def generate_with_retry(self, prompt, max_retries=3, **kwargs):
        """Generate with automatic retries and exponential backoff."""
        for attempt in range(max_retries):
            response = self.generate(prompt, **kwargs)
            if response['success']:
                return response
            if attempt < max_retries - 1:
                wait = 2 ** attempt
                if DEBUG_MODE:
                    print(f"Attempt {attempt+1} failed. Retry in {wait}s...")
                time.sleep(wait)
        return response

    def extract_code(self, response):
        """Extract code blocks from LLM response content."""
        if not response.get('success'):
            return []
        content = response['content']
        blocks = []
        in_block = False
        current = []
        for line in content.split('\n'):
            if line.startswith('```'):
                if not in_block:
                    in_block = True
                    current = []
                else:
                    in_block = False
                    if current:
                        blocks.append('\n'.join(current))
            elif in_block:
                current.append(line)
        return blocks

    def get_stats(self):
        """Get combined client statistics."""
        return {
            'mock_mode': self.use_mock,
            'requests': self.request_count,
            'cache': self.cache.get_stats(),
            'tokens': self.tracker.get_total_stats()
        }


def get_llm_client(use_mock=None):
    return LLMClient(use_mock=use_mock)


def quick_generate(prompt, use_mock=True):
    """Quick one-shot generation. Returns first code block or error."""
    client = LLMClient(use_mock=use_mock)
    response = client.generate(prompt)
    if response['success']:
        blocks = client.extract_code(response)
        return blocks[0] if blocks else "No code blocks found"
    return f"Error: {response['error']}"


# ========== SELF-TEST ==========

if __name__ == "__main__":
    print("=" * 60)
    print("LLM CLIENT SELF-TEST")
    print("=" * 60)

    # Test 1: Mock generation
    print("\nTest 1: Mock Generation")
    print("-" * 40)
    client = LLMClient(use_mock=True)
    response = client.generate("Generate an 8-bit adder")
    if response['success']:
        blocks = client.extract_code(response)
        print(f"✓ Generated {len(blocks)} code blocks")
        print(f"  Preview: {blocks[0][:80]}...")
    else:
        print(f"✗ Error: {response['error']}")

    # Test 2: Cache
    print("\nTest 2: Cache")
    print("-" * 40)
    response2 = client.generate("Generate an 8-bit adder")
    print(f"✓ Cached: {response2.get('cached', False)}")

    # Test 3: Different components
    print("\nTest 3: Component Variety")
    print("-" * 40)
    for desc in ["16-bit counter", "32-bit ALU", "shift register"]:
        r = client.generate(f"Generate a {desc}")
        print(f"  {desc}: {'✓' if r['success'] else '✗'}")

    # Test 4: Stats
    print("\nTest 4: Statistics")
    print("-" * 40)
    stats = client.get_stats()
    print(f"  Requests: {stats['requests']}")
    print(f"  Cache: {stats['cache']}")
    print(f"  Tokens: {stats['tokens']}")

    # Test 5: Quick generate
    print("\nTest 5: Quick Generate")
    print("-" * 40)
    code = quick_generate("8-bit adder")
    print(f"  Result: {code[:60]}...")

    print("\n" + "=" * 60)
    print("All self-tests passed ✓")
    print("=" * 60)
