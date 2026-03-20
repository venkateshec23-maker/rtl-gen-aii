# Free API Keys Guide - Complete Resource

## 🎓 GitHub Student Developer Pack (GitHub EDU)

### Best for Students!

#### How to Get GitHub Student Pack:
1. **Visit:** https://education.github.com/pack
2. **Click:** "Get Benefits" button
3. **Sign in** with your GitHub account
4. **Verify** you're a student:
   - School email (.edu, .ac.uk, .edu.au, etc.)
   - Or upload student ID/enrollment letter
   - Or government-issued ID showing school

#### Free Credits & Services in Pack:

| Service | Free Credits | Link |
|---------|-------------|------|
| **GitHub Copilot** | 1 year free | https://github.com/features/copilot/plans |
| **DigitalOcean** | $200 in credits | https://www.digitalocean.com/github-students |
| **AWS Educate** | $100 in credits | https://aws.amazon.com/education/awseducate/ |
| **Azure** | $100 in credits | https://azure.microsoft.com/en-us/education/ |
| **Heroku** | $50 in credits | https://www.heroku.com/ (via pack) |
| **JetBrains** | 1 year free IDE | https://www.jetbrains.com/community/education/ |

---

## 🆓 Free API Keys Available (No Card Required)

### Option 1: Use Mock LLM (Completely Free)
```python
from python.llm_client import LLMClient

# No API key needed!
client = LLMClient(use_mock=True)
response = client.generate("8-bit adder")
print(response['content'])
```
**Perfect for:** Development, testing, learning
**Cost:** Free forever

---

### Option 2: DeepSeek (Free Tier)

#### Get Free DeepSeek API Key:
1. **Visit:** https://platform.deepseek.com/
2. **Sign up** with email (no card required initially)
3. **Navigate:** API Keys section
4. **Create** new API key
5. **Copy** the key (save it securely)

#### Free Tier Includes:
- Small daily quota ($5-10 daily free credits)
- All models available
- Perfect for testing/learning

#### Use in Your App:
```python
from python.llm_client import LLMClient

client = LLMClient(
    provider='deepseek',
    api_key='sk-your-key-here',
    model='deepseek-chat'
)
response = client.generate("Create RTL code")
```

---

### Option 3: Anthropic (Claude) Free Trial

#### Get Free Anthropic API Key:
1. **Visit:** https://console.anthropic.com/
2. **Sign up** with email
3. **Verify** email
4. **Go to:** API Keys section
5. **Create** new API key

#### Free Trial:
- $5 free credits (usually enough for testing)
- After trial: ~$0.80 per 1M input tokens, $2.40 per 1M output tokens
- Start small to understand pricing

#### Use in Your App:
```python
from python.llm_client import LLMClient

client = LLMClient(
    provider='anthropic',
    api_key='sk-ant-your-key',
    model='claude-sonnet-4-20250514'
)
response = client.generate("Create RTL code")
```

---

## 🎁 Other Free LLM APIs

### 1. **Groq (Fastest Free LLM)**
- **Website:** https://console.groq.com
- **Free Tier:** Unlimited free API calls
- **Models:** LLaMA, Mixtral, Gemma
- **Speed:** Extremely fast
- **Requires:** Email only (no card)

**Setup:**
```bash
# Install Groq SDK
pip install groq

# Get API key from: https://console.groq.com/keys
```

### 2. **Replicate (Code Generation)**
- **Website:** https://replicate.com
- **Free Tier:** Free trial credits
- **Best for:** Image/code generation
- **Setup:** Email signup

### 3. **Hugging Face (Open Models)**
- **Website:** https://huggingface.co
- **Free Tier:** Unlimited access to open models
- **No API key** required initially
- **How:** Use models directly via API

---

## 📚 AWS Educate (Recommended!)

### Perfect for Students - $100 Free Credits

#### Step 1: Get AWS Educate Account
1. **Visit:** https://aws.amazon.com/education/awseducate/
2. **Click:** "Join AWS Educate"
3. **Verify** with school email
4. **Accept** terms

#### Step 2: Use Free Services
Once approved, you get:
- **AWS Bedrock:** $100+ in free credits
  - Access to Claude, Llama, and other models
  - Pay-per-token pricing
  - Great for learning

#### Step 3: In Your Code
```python
import boto3

# AWS automatically picks up credentials
bedrock = boto3.client('bedrock-runtime', region_name='us-east-1')

response = bedrock.invoke_model(
    modelId='anthropic.claude-3-sonnet-20240229-v1:0',
    body=json.dumps({"prompt": "Create 8-bit adder"})
)
```

---

## 🔧 How to Use Free Keys in Streamlit App

### Step 1: Get Your Free Key
Choose from options above (recommend: **Mock** for free testing, then **DeepSeek/Groq** for real API)

### Step 2: Add to Streamlit Secrets
Create file: `.streamlit/secrets.toml`
```toml
# Never commit this file!
DEEPSEEK_API_KEY = "sk-your-key-here"
ANTHROPIC_API_KEY = "sk-ant-your-key"
GROQ_API_KEY = "gsk-your-key"
```

### Step 3: Use in App
```python
import streamlit as st
from python.llm_client import LLMClient

# Get key from secrets
if 'deepseek_key' in st.secrets:
    api_key = st.secrets['deepseek_key']
    provider = 'deepseek'
else:
    api_key = None
    provider = 'mock'

client = LLMClient(
    provider=provider,
    api_key=api_key,
    model='deepseek-chat' if provider == 'deepseek' else None
)
```

---

## 💡 Recommended Free Stack

### For Students (GitHub EDU):
1. **Mock LLM** - Free development/testing
2. **Groq API** - Free unlimited calls (fastest)
3. **GitHub Copilot** - Free 1 year (via GitHub EDU)
4. **AWS Educate** - $100 credits

### For Non-Students:
1. **Mock LLM** - Free development
2. **DeepSeek** - Free tier quota
3. **Groq** - Completely free unlimited

---

## 📋 Step-by-Step: Get Free DeepSeek (Easiest)

### 1. Sign Up
```
Visit: https://platform.deepseek.com/
Email: your-email@example.com
Password: Choose strong password
```

### 2. Verify Email
Check email → Click verification link

### 3. Get API Key
- Click on your profile icon
- Select "API Keys"
- Click "Create API Key"
- Copy the key (save in safe place)

### 4. Test in Your Code
```python
from python.llm_client import LLMClient

api_key = "sk-xxx..." # Your key here

client = LLMClient(
    provider='deepseek',
    api_key=api_key,
    model='deepseek-chat'
)

# Test it
response = client.generate("Say hello")
print(response['content'])
```

### 5. Use in Streamlit
- Open app: `streamlit run app.py`
- Select "DeepSeek" from sidebar
- Paste your API key
- Click generate!

---

## 🔐 Security Best Practices

### ✅ DO:
- Store keys in `.env` or `.streamlit/secrets.toml`
- Add files to `.gitignore`
- Use environment variables in production
- Rotate keys regularly
- Limit key permissions

### ❌ DON'T:
- Put API keys in code files
- Commit keys to GitHub
- Share keys in messages/emails
- Use same key across services
- Leave keys in production without rotation

---

## 📊 Cost Comparison (If you eventually pay)

| Service | Cost | Speed | Quality |
|---------|------|-------|---------|
| **Mock** | Free | Fastest | Medium |
| **Groq** | Free | Fastest | High |
| **DeepSeek** | ~$0.14/1M tokens | Very Fast | High |
| **Anthropic** | ~$3-15/1M tokens | Medium | Highest |
| **AWS Bedrock** | ~$0.3-15/1M tokens | Medium | High |

---

## ✨ Recommended Action Plan

### Right Now (Today):
1. ✅ Use **Mock LLM** (free, no setup)
   ```python
   client = LLMClient(use_mock=True)
   ```

### Next (Tomorrow):
2. Get **DeepSeek free key**
   - 5 min signup: https://platform.deepseek.com/
   - Add to Streamlit
   - Test generation

### If Student (This Week):
3. Apply for **GitHub Student Pack**
   - Get $100 AWS credits
   - Free Copilot for 1 year
   - Access to other premium services

### Long Term:
4. Choose your primary provider based on needs
5. Keep Mock for development/testing
6. Use premium for production

---

## 🆘 Troubleshooting

### "Invalid API Key"
- ✅ Copy key without spaces
- ✅ Check key still active in dashboard
- ✅ Verify correct provider selected

### "Rate Limited"
- ✅ Use Mock mode for testing
- ✅ Implement caching
- ✅ Add delays between requests
- ✅ Upgrade to paid plan

### "No Free Credits Left"
- ✅ Switch to Mock LLM
- ✅ Try Groq (unlimited free)
- ✅ Wait for monthly reset
- ✅ Apply for GitHub EDU credits

---

## 📝 Summary

**TODAY:** Use Mock LLM
```python
client = LLMClient(use_mock=True)
```

**TOMORROW:** Add DeepSeek free tier
```
1. Visit https://platform.deepseek.com/
2. Sign up (2 min)
3. Get API key
4. Paste in Streamlit app
```

**THIS WEEK:** If student → Apply GitHub EDU
```
https://education.github.com/pack
```

All options are completely free to get started! 🎉

---

*Last Updated: March 19, 2026*
