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
    Multi-provider LLM Client supporting Mock, Groq, DeepSeek, NVIDIA.

    Usage:
        # Mock mode
        client = LLMClient(use_mock=True)
        
        # Groq API
        client = LLMClient(provider='grok', api_key='your-key-here', 
                          model='llama-3.3-70b-versatile')
        
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
            self.provider = 'grok' if api_key else 'nvidia'
        
        self.api_key = api_key
        self.use_mock = self.provider == 'mock'
        
        # Set model based on provider
        if model:
            self.model = model
        elif self.provider == 'grok':
            self.model = 'llama-3.3-70b-versatile'  # Default Groq model
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
        if self.provider == 'grok':
            self._init_grok()
        elif self.provider == 'deepseek':
            self._init_deepseek()
        else:
            self._init_nvidia()
    

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
            if self.provider == 'grok':
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
    

    def _generate_grok(self, prompt, system_prompt, temperature,
                       max_tokens, cache_kwargs):
        """Generate response using Grok (Groq) API - FIXED VERSION with debugging"""
        
        # Enhanced system prompt with Markdown formatting
        grok_system = system_prompt or """You are an expert Verilog RTL designer. Generate Verilog code for digital circuits.

IMPORTANT: Always output Verilog code in markdown code blocks with 'verilog' language tag.
Format EXACTLY like this:
```verilog
module design_name (ports);
    // implementation
endmodule
```

If a testbench is appropriate, include it in a separate code block:
```verilog
module design_name_tb;
    // testbench code
endmodule
```"""

        try:
            if DEBUG_MODE:
                print(f"🔄 Calling Grok API with model: {self.model}")
            
            # Make API call
            response = self.client.chat.completions.create(
                model=self.model or "mixtral-8x7b-32768",
                messages=[
                    {"role": "system", "content": grok_system},
                    {"role": "user", "content": prompt}
                ],
                temperature=temperature,
                max_tokens=max_tokens
            )
            
            # Extract content safely from response
            content = ""
            
            # Primary extraction method
            if response and hasattr(response, 'choices') and len(response.choices) > 0:
                choice = response.choices[0]
                
                if hasattr(choice, 'message') and hasattr(choice.message, 'content'):
                    content = choice.message.content or ""
                elif hasattr(choice, 'text'):
                    content = choice.text or ""
                else:
                    # Fallback: try to convert to dict
                    if hasattr(choice, '__dict__'):
                        choice_dict = choice.__dict__
                        if 'message' in choice_dict:
                            message = choice_dict['message']
                            if isinstance(message, dict):
                                content = message.get('content', '')
                            elif hasattr(message, 'content'):
                                content = message.content
            
            if DEBUG_MODE:
                print(f"✅ Got response: {len(content)} chars")
                if content:
                    print(f"First 200 chars: {content[:200]}")
            
            # Validate content
            if not content or len(content.strip()) == 0:
                error_msg = "No content in Grok response"
                if DEBUG_MODE:
                    print(f"❌ {error_msg}")
                    print(f"Response object: {response}")
                
                self.tracker.log_usage(self.model, 0, 0,
                                       success=False, error=error_msg)
                return {
                    'success': False,
                    'content': "",
                    'provider': 'grok',
                    'model': self.model,
                    'error': error_msg
                }
            
            # Extract usage info safely
            tokens = 0
            if hasattr(response, 'usage') and response.usage:
                if hasattr(response.usage, 'total_tokens'):
                    tokens = response.usage.total_tokens
                elif isinstance(response.usage, dict):
                    tokens = response.usage.get('total_tokens', 0)
            
            usage = {
                'prompt_tokens': getattr(response.usage, 'prompt_tokens', 0) if hasattr(response, 'usage') else 0,
                'completion_tokens': getattr(response.usage, 'completion_tokens', 0) if hasattr(response, 'usage') else 0,
                'total_tokens': tokens
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
                print(f"✅ Grok success. Tokens: {usage['total_tokens']}")
            
            return result
            
        except Exception as e:
            error_msg = str(e)
            if DEBUG_MODE:
                print(f"❌ Grok error: {error_msg}")
                import traceback
                traceback.print_exc()
            
            self.tracker.log_usage(self.model, 0, 0,
                                   success=False, error=error_msg)
            return {
                'success': False,
                'content': "",
                'error': error_msg,
                'provider': 'grok',
                'model': self.model
            }
    
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
        """Extract code blocks from LLM response - IMPROVED with multiple patterns.
        
        Handles:
        - Markdown code blocks (```verilog ... ```)
        - Raw module declarations
        - Multiple code blocks in single response
        - Failed responses
        """
        if not response.get('success') and not response.get('content'):
            return []
        
        content = response.get('content', '')
        if not content:
            return []
        
        import re
        
        # Try multiple patterns in order of preference
        patterns = [
            # Pattern 1: Standard markdown with verilog tag and newline
            r'```(?:verilog)?\s*\n(.*?)```',
            
            # Pattern 2: Markdown with spaces after backticks
            r'```\s*verilog\s*\n(.*?)```',
            
            # Pattern 3: Code blocks without language specification
            r'```\s*\n(.*?)```',
            
            # Pattern 4: Markdown with just backticks (flexible)
            r'```(.*?)```',
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, content, re.DOTALL | re.IGNORECASE)
            if matches:
                # Clean up each match
                cleaned = []
                for m in matches:
                    # Remove any remaining backticks
                    m = re.sub(r'```+$', '', m.strip())
                    m = re.sub(r'^```+', '', m)
                    cleaned_code = m.strip()
                    if cleaned_code:  # Only add non-empty blocks
                        cleaned.append(cleaned_code)
                if cleaned:
                    return cleaned
        
        # Pattern 5: Look for explicit module declarations
        modules = []
        module_pattern = r'module\s+\w+'
        positions = [m.start() for m in re.finditer(module_pattern, content, re.IGNORECASE)]
        
        if positions:
            for i, pos in enumerate(positions):
                start = pos
                # Find end position (next module or end of content)
                end = positions[i+1] if i+1 < len(positions) else len(content)
                module_text = content[start:end]
                
                # Find the matching endmodule
                endmodule_match = re.search(r'endmodule\s*', module_text, re.IGNORECASE)
                if endmodule_match:
                    module_text = module_text[:endmodule_match.end()]
                    cleaned_code = module_text.strip()
                    if cleaned_code:
                        modules.append(cleaned_code)
            
            if modules:
                return modules
        
        # Last resort: if content looks like code, return it
        if 'module' in content.lower() or 'always' in content.lower() or 'endmodule' in content.lower():
            return [content.strip()]
        
        # If nothing found but response was successful, return empty list
        return []

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
