# DeepSeek LLM Provider Integration - Complete Guide

## Overview

The RTL-Gen AI application now supports multiple LLM providers for maximum flexibility:
- **Mock LLM** - Free testing (no API key needed)
- **Anthropic (Claude)** - Premium Claude models
- **DeepSeek** - High-performance open models

## Changes Made

### 1. Backend Refactoring - `python/llm_client.py`

#### **New `__init__` Method**
```python
def __init__(self, use_mock=None, cache_manager=None, token_tracker=None,
             api_key=None, model=None, provider=None):
```

**Parameters:**
- `use_mock` - Legacy parameter for backward compatibility
- `api_key` - API key for Anthropic or DeepSeek
- `model` - Specific model to use (provider-dependent)
- `provider` - Provider name: `'mock'`, `'anthropic'`, or `'deepseek'`

#### **New Provider Methods**
```python
def _init_anthropic()      # Initialize Anthropic Claude client
def _init_deepseek()       # Initialize DeepSeek API client
def _init_nvidia()         # Initialize NVIDIA-hosted DeepSeek client
```

#### **New Generation Methods**
```python
def _generate_anthropic()           # Handle Anthropic API calls
def _generate_openai_compatible()   # Handle DeepSeek/NVIDIA API calls
```

### 2. Frontend Updates - `app.py`

#### **New Provider Selector**
```python
llm_provider = st.selectbox(
    "LLM Provider",
    ["Mock (Free - No API Key)", "Anthropic (Claude)", "DeepSeek"],
    help="Choose your preferred LLM provider"
)
```

#### **Conditional Configuration Fields**
- Mock: No configuration needed
- Anthropic: API key + model selection
- DeepSeek: API key + model selection

#### **Provider Initialization**
```python
# Determine provider name for LLMClient
if use_mock:
    provider_name = 'mock'
elif llm_provider == "Anthropic (Claude)":
    provider_name = 'anthropic'
elif llm_provider == "DeepSeek":
    provider_name = 'deepseek'
else:
    provider_name = 'mock'

client = LLMClient(use_mock=use_mock, api_key=api_key, 
                  model=model, provider=provider_name)
```

### 3. Dependencies

**Installed:**
- `openai` - For DeepSeek API compatibility
- `anthropic` - Already installed for Claude support

## Usage Guide

### Mock Provider (Testing/Development)

```python
from python.llm_client import LLMClient

# Initialize Mock client
client = LLMClient(use_mock=True)

# Generate RTL
response = client.generate("Create an 8-bit adder")
if response['success']:
    print(response['content'])
```

**Advantages:**
- No API key required
- Free for unlimited testing
- Fast responses
- Perfect for development

### Anthropic Provider (Claude Models)

#### Step 1: Get API Key
1. Visit https://console.anthropic.com
2. Navigate to API Keys section
3. Create new API key
4. Copy and save securely

#### Step 2: Use in Code
```python
from python.llm_client import LLMClient

client = LLMClient(
    provider='anthropic',
    api_key='sk-ant-your-key-here',
    model='claude-sonnet-4-20250514'
)

response = client.generate("Create an 8-bit adder")
```

#### Step 3: Use in Streamlit UI
1. Open http://localhost:8501
2. Select "Anthropic (Claude)" from sidebar
3. Paste API key in the text field
4. Select desired Claude model
5. Enter design description and generate

**Available Models:**
- `claude-sonnet-4-20250514` - Latest, fastest
- `claude-opus-4-20250514` - Most powerful
- `claude-3-5-sonnet-20241022` - Stable version

### DeepSeek Provider

#### Step 1: Get API Key
1. Visit https://platform.deepseek.com
2. Create account or log in
3. Navigate to API Keys
4. Create new API key
5. Copy and save securely

#### Step 2: Use in Code
```python
from python.llm_client import LLMClient

client = LLMClient(
    provider='deepseek',
    api_key='sk-your-deepseek-key',
    model='deepseek-chat'
)

response = client.generate("Create an 8-bit adder")
```

#### Step 3: Use in Streamlit UI
1. Open http://localhost:8501
2. Select "DeepSeek" from sidebar
3. Paste API key in the text field
4. Select desired DeepSeek model
5. Enter design description and generate

**Available Models:**
- `deepseek-chat` - General purpose, fastest
- `deepseek-coder` - Code generation optimized
- `deepseek-reasoner` - Advanced reasoning

## API Key Security

### Best Practices
1. **Never commit keys** to version control
2. **Use environment variables** for production:
   ```python
   import os
   api_key = os.getenv('ANTHROPIC_API_KEY')
   ```

3. **Use `.env` files** (keep in `.gitignore`):
   ```
   ANTHROPIC_API_KEY=sk-ant-...
   DEEPSEEK_API_KEY=sk-...
   ```

4. **Streamlit secrets** for cloud deployment:
   ```
   # .streamlit/secrets.toml
   ANTHROPIC_API_KEY = "sk-ant-..."
   DEEPSEEK_API_KEY = "sk-..."
   ```

   Access in code:
   ```python
   import streamlit as st
   api_key = st.secrets["ANTHROPIC_API_KEY"]
   ```

## Testing

### Integration Test
```python
from python.llm_client import LLMClient

# Test all three providers
clients = {
    'mock': LLMClient(use_mock=True),
    'anthropic': LLMClient(provider='anthropic', api_key='key', model='claude-sonnet-4-20250514'),
    'deepseek': LLMClient(provider='deepseek', api_key='key', model='deepseek-chat')
}

for name, client in clients.items():
    print(f"Testing {name}...")
    response = client.generate("Create 4-bit adder")
    print(f"  Success: {response['success']}")
    print(f"  Tokens: {response['usage']['total_tokens']}")
```

### Run Tests
```bash
python -m pytest tests/test_llm_client.py -v
```

## Performance Comparison

| Provider | Speed | Cost | Quality | Ideal For |
|----------|-------|------|---------|-----------|
| Mock | Fastest | Free | Medium | Development/Testing |
| Anthropic (Claude) | Medium | Paid | Highest | Production/Premium |
| DeepSeek | Fast | Low | High | Production/Budget |

## Troubleshooting

### "openai package required" Error
```bash
pip install openai
```

### "API key required" Error
- Mock: No API key needed, just select Mock provider
- Anthropic: Visit https://console.anthropic.com and get key
- DeepSeek: Visit https://platform.deepseek.com and get key

### "Invalid API Key" Error
- Check key is copied correctly (no extra spaces)
- Verify key is still active in provider dashboard
- For DeepSeek: Ensure using direct API (not NVIDIA-hosted)

### Slow Response Times
- Mock: Already fastest option
- Anthropic: Try Sonnet model (faster than Opus)
- DeepSeek: Try deepseek-chat (faster than reasoner)

## Configuration Examples

### Production Setup with .env
```
# .env file
MOCK_LLM_ENABLED=false
ANTHROPIC_API_KEY=sk-ant-your-production-key
DEEPSEEK_API_KEY=sk-your-deepseek-key
DEFAULT_PROVIDER=anthropic
```

### Streamlit with Multi-Provider
```python
# app.py
import os
from python.llm_client import LLMClient

provider = os.getenv('DEFAULT_PROVIDER', 'mock')
api_key = os.getenv(f'{provider.upper()}_API_KEY')

if provider == 'mock':
    client = LLMClient(use_mock=True)
else:
    client = LLMClient(
        provider=provider,
        api_key=api_key,
        model='default-model'
    )
```

## Migration Guide

### From Old Code
```python
# Old: Single provider support
client = LLMClient(use_mock=True)  # OR
client = LLMClient()               # Uses config defaults
```

### To New Code
```python
# New: Explicit multi-provider support
client = LLMClient(use_mock=True)                    # Mock
client = LLMClient(provider='anthropic',             # Anthropic
                   api_key='sk-ant-...', 
                   model='claude-sonnet-4-20250514')
client = LLMClient(provider='deepseek',              # DeepSeek
                   api_key='sk-...', 
                   model='deepseek-chat')
```

## Backward Compatibility

✅ **Fully backward compatible** - Old code using `use_mock` parameter still works:
```python
# Still works (legacy)
client = LLMClient(use_mock=True)

# New preferred way
client = LLMClient(provider='mock')
```

## Documentation Updates

| File | Changes |
|------|---------|
| `python/llm_client.py` | Multi-provider support, new methods |
| `app.py` | Provider selector UI, conditional fields |
| `requirements.txt` | Added openai package |
| This file | New documentation |

## Support

For issues or questions:
1. Check troubleshooting section above
2. Review test cases in `tests/test_llm_client.py`
3. Verify provider API keys in respective dashboards
4. Check deployment documentation in `docs/DEPLOYMENT.md`

## Version Information

- **RTL-Gen AI Version:** 1.0.0
- **LLMClient Version:** 2.0.0 (Multi-provider)
- **Anthropic SDK:** 0.86.0+
- **OpenAI SDK:** 1.0.0+ (for DeepSeek)

---

**Last Updated:** March 19, 2026
**Status:** Production Ready
