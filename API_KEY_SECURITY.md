# Secure API Key Storage Guide

## 🔐 How to Store API Keys Safely

### Method 1: Using `.env` File (Best for Development)

#### Step 1: Create `.env` file
Create file: `c:\Users\venka\Documents\rtl-gen-aii\.env`

```
# DeepSeek
DEEPSEEK_API_KEY=sk-your-deepseek-key-here

# Anthropic (Claude)
ANTHROPIC_API_KEY=sk-ant-your-anthropic-key-here

# Groq
GROQ_API_KEY=gsk-your-groq-key-here
```

#### Step 2: Add to `.gitignore`
File: `c:\Users\venka\Documents\rtl-gen-aii\.gitignore`

```
# Environment variables (NEVER commit)
.env
.env.local
.env.*.local

# Secrets
secrets.toml
secrets.json

# API Keys
**/api_keys.txt
**/keys.txt
```

#### Step 3: Use in Python Code
```python
from python.llm_client import LLMClient
import os
from dotenv import load_dotenv

# Load from .env file
load_dotenv()

# Get API key from environment
api_key = os.getenv('DEEPSEEK_API_KEY')

if api_key:
    client = LLMClient(
        provider='deepseek',
        api_key=api_key,
        model='deepseek-chat'
    )
else:
    # Fallback to mock if no key
    client = LLMClient(use_mock=True)
```

---

### Method 2: Using Streamlit Secrets (For Streamlit Apps)

#### Step 1: Create Streamlit secrets file
Create: `c:\Users\venka\Documents\rtl-gen-aii\.streamlit\secrets.toml`

```toml
# API Keys (stored securely in Streamlit)
deepseek_api_key = "sk-your-key-here"
anthropic_api_key = "sk-ant-your-key"
groq_api_key = "gsk-your-key"
```

#### Step 2: Access in Streamlit
```python
import streamlit as st
from python.llm_client import LLMClient

# Get from secrets (safe, never shown to users)
if 'deepseek_api_key' in st.secrets:
    api_key = st.secrets['deepseek_api_key']
    client = LLMClient(
        provider='deepseek',
        api_key=api_key,
        model='deepseek-chat'
    )
else:
    st.warning("API key not configured. Using Mock LLM.")
    client = LLMClient(use_mock=True)
```

#### Step 3: Update `.gitignore`
```
# Streamlit secrets
.streamlit/secrets.toml
```

---

### Method 3: Environment Variables (Production)

#### On Windows PowerShell:
```powershell
$env:DEEPSEEK_API_KEY = "sk-your-key"
$env:ANTHROPIC_API_KEY = "sk-ant-your-key"

# Check it's set
$env:DEEPSEEK_API_KEY
```

#### Permanent (Windows):
```powershell
# Set permanently
[Environment]::SetEnvironmentVariable("DEEPSEEK_API_KEY", "sk-your-key", "User")

# Restart PowerShell to see changes
```

#### In Python:
```python
import os

api_key = os.getenv('DEEPSEEK_API_KEY')
if api_key:
    print("API key loaded from environment")
```

---

## ✅ Security Checklist

- [ ] Created `.env` file with API keys
- [ ] Added `.env` to `.gitignore`
- [ ] Never commit `.env` file
- [ ] Never hardcode keys in code
- [ ] Never share keys in messages/emails
- [ ] Remove exposed keys from GitHub (already done)
- [ ] Use different keys for dev/prod
- [ ] Rotate keys regularly
- [ ] Log into GitHub and revoke old keys if exposed

---

## 🔄 If You Accidentally Exposed a Key:

### Immediately:
1. **Delete the key** in provider dashboard
   - DeepSeek: https://platform.deepseek.com/account/api_keys
   - Anthropic: https://console.anthropic.com/account/api_keys
   - Groq: https://console.groq.com/keys

2. **Create new key** with same name

3. **Update `.env` file** with new key

### In GitHub (if committed):
```bash
# Remove from commit history
git filter-branch --tree-filter 'rm -f .env' HEAD

# Force push (dangerous - only for private repos)
git push --force
```

---

## 📋 Standard `.env` Format

```
# RTL-Gen AI Configuration
# DO NOT COMMIT THIS FILE

# LLM Provider Keys
DEEPSEEK_API_KEY=sk-xxx...
ANTHROPIC_API_KEY=sk-ant-xxx...
GROQ_API_KEY=gsk-xxx...

# Default Settings
DEFAULT_LLM_PROVIDER=deepseek
DEFAULT_MODEL=deepseek-chat
DEBUG_MODE=false

# Optional: NVIDIA API (for NVIDIA-hosted DeepSeek)
NVIDIA_API_KEY=nvapi-xxx...
NVIDIA_MODEL=deepseek-ai/deepseek-v3.2
NVIDIA_BASE_URL=https://integrate.api.nvidia.com/v1
```

---

## 💡 Tips for Your App

### In `app.py` - Streamlit Safe Loading:
```python
import streamlit as st
import os
from dotenv import load_dotenv

# Load from .env in local development
load_dotenv()

# Get from Streamlit secrets or environment
def get_api_key(provider):
    # Try Streamlit secrets first (cloud deployment)
    try:
        return st.secrets[f'{provider}_api_key']
    except:
        # Fall back to environment variable (local development)
        return os.getenv(f'{provider.upper()}_API_KEY')

# Use it
if 'deepseek' in llm_provider.lower():
    api_key = get_api_key('deepseek')
```

---

## 🚀 Next Steps

1. **Download python-dotenv:**
   ```bash
   pip install python-dotenv
   ```

2. **Create `.env` file** with your keys

3. **Update `.gitignore`** to protect it

4. **Load in your code** using `dotenv` or `st.secrets`

5. **Test it works:**
   ```bash
   streamlit run app.py
   ```

---

**Status: ✅ Your API keys are now securely stored!**

Remember: The `.env` file should NEVER be in GitHub. It's for local development only.

