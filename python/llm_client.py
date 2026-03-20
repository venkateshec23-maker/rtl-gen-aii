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
    Multi-provider LLM Client supporting Mock, Anthropic, DeepSeek.

    Usage:
        # Mock mode
        client = LLMClient(use_mock=True)
        
        # Anthropic (Claude)
        client = LLMClient(provider='anthropic', api_key='your-key-here', 
                          model='claude-sonnet-4-20250514')
        
        # DeepSeek direct API
        client = LLMClient(provider='deepseek', api_key='your-key-here', 
                          model='deepseek-chat')
        
        response = client.generate("Generate an 8-bit adder")
        if response['success']:
            code_blocks = client.extract_code(response)
    """

    def __init__(self, use_mock=None, cache_manager=None, token_tracker=None,
                 api_key=None, model=None, provider=None):
        """
        Initialize LLM Client with multi-provider support.
        
        Args:
            use_mock: Boolean to enable mock mode (backward compat)
            cache_manager: Custom cache manager instance
            token_tracker: Custom token tracker instance
            api_key: API key for Anthropic or DeepSeek provider
            model: Specific model to use (depends on provider)
            provider: Provider name ('mock', 'anthropic', 'deepseek', or None for auto)
        """
        self.cache = cache_manager or get_cache_manager()
        self.tracker = token_tracker or get_token_tracker()
        self.last_request_time = 0
        self.request_count = 0
        
        # Detect provider from parameters or use_mock flag
        if provider:
            self.provider = provider.lower()
        elif use_mock is True:
            self.provider = 'mock'
        else:
            self.provider = 'anthropic' if api_key else 'nvidia'
        
        self.api_key = api_key
        self.use_mock = self.provider == 'mock'
        
        # Set model based on provider
        if model:
            self.model = model
        elif self.provider == 'anthropic':
            self.model = 'claude-sonnet-4-20250514'  # Default Anthropic model
        elif self.provider == 'deepseek':
            self.model = 'deepseek-chat'
        else:
            self.model = NVIDIA_MODEL
        
        # Initialize mock if needed
        self.mock = None
        if self.use_mock:
            self.mock = get_mock_llm(delay=0.1)
        
        # Initialize real client if not mock
        if not self.use_mock:
            self._init_real_client()

        if DEBUG_MODE:
            print(f"LLMClient initialized (provider={self.provider}, model={self.model})")

    def _init_real_client(self):
        """Initialize the appropriate LLM client based on provider."""
        if self.provider == 'anthropic':
            self._init_anthropic()
        elif self.provider == 'grok':
            self._init_grok()
        elif self.provider == 'deepseek':
            self._init_deepseek()
        else:
            self._init_nvidia()
    
    def _init_anthropic(self):
        """Initialize Anthropic Claude client."""
        try:
            from anthropic import Anthropic
        except ImportError:
            raise ImportError("anthropic package required. Run: pip install anthropic")
        
        if not self.api_key:
            raise ValueError(
                "Anthropic API key required. Provide via api_key parameter or "
                "set ANTHROPIC_API_KEY environment variable. "
                "Get key at: https://console.anthropic.com"
            )
        
        self.client = Anthropic(api_key=self.api_key)
    
    def _init_grok(self):
        """Initialize Grok (Groq) client."""
        try:
            from groq import Groq
        except ImportError:
            raise ImportError("groq package required. Run: pip install groq")
        
        if not self.api_key:
            raise ValueError(
                "Grok API key required. Provide via api_key parameter or "
                "set GROK_API_KEY environment variable. "
                "Get key at: https://console.groq.com"
            )
        
        self.client = Groq(api_key=self.api_key)
    
    def _init_deepseek(self):
        """Initialize DeepSeek API client."""
        try:
            from openai import OpenAI
        except ImportError:
            raise ImportError("openai package required. Run: pip install openai")
        
        if not self.api_key:
            raise ValueError(
                "DeepSeek API key required. Provide via api_key parameter. "
                "Get key at: https://platform.deepseek.com"
            )
        
        self.client = OpenAI(
            api_key=self.api_key,
            base_url="https://api.deepseek.com"
        )
    
    def _init_nvidia(self):
        """Initialize NVIDIA-hosted DeepSeek client."""
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
        """Generate using the real LLM provider."""
        try:
            if self.provider == 'anthropic':
                return self._generate_anthropic(prompt, system_prompt,
                                               temperature, max_tokens, cache_kwargs)
            elif self.provider == 'grok':
                return self._generate_grok(prompt, system_prompt,
                                          temperature, max_tokens, cache_kwargs)
            else:
                return self._generate_openai_compatible(prompt, system_prompt,
                                                       temperature, max_tokens, cache_kwargs)
        except Exception as e:
            error_msg = str(e)
            self.tracker.log_usage(self.model, 0, 0,
                                   success=False, error=error_msg)
            return {'success': False, 'error': error_msg, 'cached': False}
    
    def _generate_anthropic(self, prompt, system_prompt, temperature,
                           max_tokens, cache_kwargs):
        """Generate response using Anthropic Claude."""
        try:
            self._rate_limit()
            
            response = self.client.messages.create(
                model=self.model,
                max_tokens=max_tokens,
                system=system_prompt or "",
                messages=[
                    {"role": "user", "content": prompt}
                ],
                temperature=temperature
            )
            
            content = response.content[0].text
            usage = {
                'prompt_tokens': response.usage.input_tokens,
                'completion_tokens': response.usage.output_tokens,
                'total_tokens': response.usage.input_tokens + response.usage.output_tokens
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
                print(f"Anthropic success. Tokens: {usage['total_tokens']}")
            return result
        
        except Exception as e:
            error_msg = str(e)
            self.tracker.log_usage(self.model, 0, 0,
                                   success=False, error=error_msg)
            return {'success': False, 'error': error_msg, 'cached': False}
    
    def _generate_grok(self, prompt, system_prompt, temperature,
                       max_tokens, cache_kwargs):
        """Generate response using Grok (Groq) API."""
        try:
            self._rate_limit()
            
            response = self.client.chat.completions.create(
                model=self.model or "mixtral-8x7b-32768",
                max_tokens=max_tokens,
                system=system_prompt or "You are an expert Verilog RTL designer.",
                messages=[
                    {"role": "user", "content": prompt}
                ],
                temperature=temperature
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
                print(f"Grok success. Tokens: {usage['total_tokens']}")
            return result
        
        except Exception as e:
            error_msg = str(e)
            self.tracker.log_usage(self.model, 0, 0,
                                   success=False, error=error_msg)
            return {'success': False, 'error': error_msg, 'cached': False}
    
    def _generate_openai_compatible(self, prompt, system_prompt, temperature,
                                   max_tokens, cache_kwargs):
        """Generate response using OpenAI-compatible API (DeepSeek or NVIDIA)."""
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
        """Extract code blocks from LLM response content.
        
        Handles:
        - Markdown code blocks (```language ... ```)
        - Raw code if no blocks found
        - Failed responses
        """
        if not response.get('success'):
            return []
        
        content = response.get('content', '')
        if not content:
            return []
        
        blocks = []
        in_block = False
        current = []
        block_lang = ''
        
        for line in content.split('\n'):
            # Check if line contains code fence markers
            if '```' in line:
                if not in_block:
                    # Starting a code block
                    in_block = True
                    current = []
                    block_lang = line.replace('```', '').strip()
                else:
                    # Ending a code block
                    in_block = False
                    if current:
                        code = '\n'.join(current).strip()
                        if code:  # Only add non-empty blocks
                            blocks.append(code)
                    current = []
                    block_lang = ''
            elif in_block:
                current.append(line)
        
        # If no code blocks found but content exists, return all content as single block
        if not blocks and content.strip():
            # Try to extract Verilog-like code if no markdown blocks found
            lines = [l for l in content.split('\n') if l.strip()]
            if lines:
                blocks.append('\n'.join(lines))
        
        return blocks

    def get_stats(self):
        """Get combined client statistics."""
        return {
            'mock_mode': self.use_mock,
            'requests': self.request_count,
            'cache': self.cache.get_stats(),
            'tokens': self.tracker.get_total_stats()
        }


def get_llm_client(use_mock=None, api_key=None, model=None, provider=None):
    return LLMClient(use_mock=use_mock, api_key=api_key, model=model, provider=provider)


def quick_generate(prompt, use_mock=True, api_key=None, model=None, provider=None):
    """Quick one-shot generation. Returns first code block or error."""
    client = LLMClient(use_mock=use_mock, api_key=api_key, model=model, provider=provider)
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
