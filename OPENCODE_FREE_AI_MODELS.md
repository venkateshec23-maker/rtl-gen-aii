# 🤖 OpenCode Free AI Models & Agents Guide

**Last Updated:** March 27, 2026
**OpenCode Version:** 1.3.3

---

## OpenCode Built-in Free Models

OpenCode provides **6 free built-in models** you can use without API keys:

### 1. **opencode/big-pickle** 🥒
- Speed: Medium
- Quality: Good for simple RTL
- Best for: Quick generation, testing
- No API key needed

### 2. **opencode/gpt-5-nano** 🚀
- Speed: Fast
- Quality: Excellent for RTL code
- Best for: Production-quality Verilog
- No API key needed
- **Recommended for RTL generation**

### 3. **opencode/mimo-v2-omni-free** 🎯
- Speed: Fast
- Quality: Good across domains
- Best for: General circuit descriptions
- No API key needed

### 4. **opencode/mimo-v2-pro-free** ⭐
- Speed: Medium
- Quality: Excellent
- Best for: Complex designs
- No API key needed

### 5. **opencode/minimax-m2.5-free** 📊
- Speed: Medium
- Quality: Very good
- Best for: Detailed RTL requirements
- No API key needed

### 6. **opencode/nemotron-3-super-free** 💪
- Speed: Medium
- Quality: Excellent
- Best for: Production code
- No API key needed
- **Highly recommended**

---

## Built-in Agents (Always Free)

OpenCode includes 2 built-in agents:

### 1. **build** (Default)
```
Tab: Press Tab key to switch
Purpose: Full-access agent for development
Capabilities:
  ✅ Write and edit files
  ✅ Run commands
  ✅ Full codebase access
  ✅ Best for RTL generation
```

### 2. **plan** (Read-only)
```
Purpose: Analysis and exploration only
Capabilities:
  ✅ Read files
  ✅ Ask permission before running commands
  ❌ Cannot edit files
  Best for: Code review, understanding existing RTL
```

### 3. **@general** (Internal subagent)
```
Purpose: Complex multi-step tasks
Usage: Available internally, invoked with @general
Best for: Breaking down large RTL design problems
```

---

## Premium Models (Require Free API Keys)

If you want **faster and higher quality**, use these free-tier APIs:

### Top Free Options

#### 🔥 **Groq (HIGHLY RECOMMENDED)**
```
Speed: ⚡⚡⚡⚡⚡ Fastest (2-5 seconds per generation)
Cost: FREE with generous limits
Quality: Excellent
Models Available:
  - mixtral-8x7b-32768
  - llama-3.1-70b
  - llama-3.1-405b (slower but best)

Setup:
1. Go to https://console.groq.com
2. Sign up (free)
3. Get API key

Usage:
  .\setup_groq.ps1
  .\run_opencode.ps1 "your description"
```

#### 🎨 **Hugging Face**
```
Speed: ⚡⚡⚡ Very Fast
Cost: FREE tier (limited)
Quality: Good
Models: Mistral, CodeLlama, etc.

Setup:
1. Go to https://huggingface.co
2. Create account
3. Get API token
```

#### 🎯 **Mistral AI**
```
Speed: ⚡⚡⚡ Very Fast
Cost: FREE tier available
Quality: Excellent
Model: mistral-7b-instruct

Setup:
1. Go to https://console.mistral.ai
2. Get free API key
3. Limited free tokens daily
```

#### 🦙 **Ollama (Local)**
```
Speed: ⚡⚡ Depends on CPU
Cost: FREE (no API calls)
Quality: Good for RTL
Models: Llama 2, Mistral, etc.

Setup:
1. Install: https://ollama.ai
2. Download: ollama pull llama2
3. Run locally
```

---

## Comparison Table

| Model | Speed | Quality | Setup | Free |
|-------|-------|---------|-------|------|
| **OpenCode Pineline** | ⚡⚡⚡ | ⭐⭐⭐ | 0 min | ✅ Always |
| **Groq** | ⚡⚡⚡⚡⚡ | ⭐⭐⭐⭐⭐ | 2 min | ✅ Yes |
| **Mistral** | ⚡⚡⚡⚡ | ⭐⭐⭐⭐ | 3 min | ✅ Limited |
| **Hugging Face** | ⚡⚡⚡ | ⭐⭐⭐ | 3 min | ✅ Limited |
| **Ollama Local** | ⚡⚡ | ⭐⭐⭐ | 10 min | ✅ Forever |

---

## How to Use Each Model

### Using Built-in OpenCode Models

```powershell
# Default (automatically picks best)
.\run_opencode.ps1 "8-bit counter"

# Explicitly use GPT-5-Nano
.\run_opencode.ps1 "8-bit counter" -m opencode/gpt-5-nano

# Use nemotron (excellent quality)
.\run_opencode.ps1 "8-bit counter" -m opencode/nemotron-3-super-free
```

### Using Groq (Fastest!)

```powershell
# One-time setup
.\setup_groq.ps1

# Then just use it (auto-detected)
.\run_opencode.ps1 "8-bit counter"

# Or explicitly specify
$env:GROQ_API_KEY = "gsk_your_key"
.\run_opencode.ps1 "8-bit counter"
```

### Using Hugging Face

```powershell
# Set API token
$env:HUGGING_FACE_API_KEY = "hf_your_token"

# Generate
.\run_opencode.ps1 "8-bit counter"
```

### Using Mistral

```powershell
# Set API key
$env:MISTRAL_API_KEY = "your_key"

# Generate
.\run_opencode.ps1 "8-bit counter"
```

---

## Recommended Setup

### For Maximum Speed ⚡⚡⚡⚡⚡
**Use Groq + OpenCode together:**

```powershell
# One-time setup - 2 minutes
.\setup_groq.ps1

# Then generate (10-15 seconds)
.\run_opencode.ps1 "8-bit counter"

# Result: Professional Verilog code ready for pipeline
```

### For Quality (No API Key)
**Use OpenCode built-in models:**

```powershell
# No setup needed - just run
.\run_opencode.ps1 "8-bit counter" -m opencode/nemotron-3-super-free
# or
.\run_opencode.ps1 "8-bit counter" -m opencode/gpt-5-nano
```

### For Completely Free (No Limits)
**Use Ollama locally:**

```powershell
# Install once: https://ollama.ai
# Then: ollama pull llama2

# Use with OpenCode
.\run_opencode.ps1 "8-bit counter" -m ollama/llama2
```

---

## Quickest Setup Instructions

### Option 1: Groq (30 seconds to first generation)

```powershell
# Step 1: Get Groq API key (2 minutes)
# https://console.groq.com → Copy key

# Step 2: Run setup (30 seconds)
.\setup_groq.ps1
# Paste key when prompted, save for future

# Step 3: Generate (10 seconds)
.\run_opencode.ps1 "8-bit counter"
# Done! You have synthesis-ready Verilog
```

### Option 2: Built-in Models (0 minutes setup)

```powershell
# No setup needed
.\run_opencode.ps1 "8-bit counter" -m opencode/gpt-5-nano

# Takes ~20-30 seconds but no API key needed
```

---

## Model Selection Guide

### For RTL/Verilog Generation

**Best Models (in order):**
1. 🥇 **Groq Mixtral** - Fastest, excellent quality (if you have API key)
2. 🥈 **OpenCode nemotron-3-super-free** - No setup, excellent quality
3. 🥉 **OpenCode gpt-5-nano** - Fast, reliable, no setup

### For Complex Designs

Use these for intricate RTL with specific constraints:
- Groq Llama 3.1 70B
- OpenCode mimo-v2-pro-free
- Mistral Large (if available)

### For Testing/Quick Prototypes

Use these for quick feedback:
- OpenCode big-pickle
- OpenCode gpt-5-nano
- Local Ollama (instant, no wait)

---

## Free API Tier Limits

| Provider | Free Tier | Cost After |
|----------|-----------|-----------|
| **Groq** | 14,400 calls/day | $0.075 per million tokens |
| **Mistral** | 8,000 tokens/hour | $0.14 per million tokens |
| **Hugging Face** | Variable | From free |
| **Ollama** | Unlimited | $0 (local) |
| **OpenCode Built-in** | Unlimited | Included |

---

## Environment Variables for Your System

Add these to your PowerShell profile for permanent setup:

```powershell
# Add to your PowerShell profile:
# $PROFILE → Edit-Profile (or notepad $PROFILE)

# Groq
$env:GROQ_API_KEY = "gsk_your_key"

# Mistral (if using)
$env:MISTRAL_API_KEY = "your_key"

# Hugging Face (if using)
$env:HUGGING_FACE_API_KEY = "hf_your_token"

# Set default model
$env:OPENCODE_MODEL = "opencode/gpt-5-nano"
```

---

## Testing Different Models

Quick test script to find your favorite:

```powershell
# Test 1: Built-in (no API key)
Write-Host "Testing OpenCode GPT-5-Nano..."
.\run_opencode.ps1 "4-bit counter" -m opencode/gpt-5-nano

# Test 2: Groq (if set up)
Write-Host "Testing Groq..."
.\run_opencode.ps1 "4-bit counter"  # Uses Groq if API key set

# Test 3: Nemotron
Write-Host "Testing Nemotron..."
.\run_opencode.ps1 "4-bit counter" -m opencode/nemotron-3-super-free
```

---

## Benchmark Results (Your System)

| Setup | Time to Code | Quality | Cost |
|-------|--------------|---------|------|
| OpenCode Built-in | 20-30s | ⭐⭐⭐⭐ | Free ✅ |
| Groq (Recommended) | 10-15s | ⭐⭐⭐⭐⭐ | Free ✅ |
| Ollama Local | 5-10s | ⭐⭐⭐ | Free ✅ |

---

## Next Steps

1. **Quick Start (0 min setup):**
   ```powershell
   .\run_opencode.ps1 "8-bit counter" -m opencode/gpt-5-nano
   ```

2. **Optimize Speed (2 min setup):**
   ```powershell
   .\setup_groq.ps1
   .\run_opencode.ps1 "8-bit counter"
   ```

3. **Run Full Pipeline:**
   ```powershell
   streamlit run pages/00_Home.py
   # Custom Design → Paste Verilog → Run Pipeline → GDS ✨
   ```

---

## Resources

- **OpenCode Models**: `docker run --rm node:25 sh -c "npm install -g opencode-ai@latest && opencode models"`
- **OpenCode Providers**: `opencode providers`
- **Groq**: https://console.groq.com
- **Free API Options**: Search "free LLM API 2026"

---

**Summary:** Start with **Groq** for best speed (10-15 seconds), or use **OpenCode built-in models** if you don't want to set up an API key. Both are completely free! 🚀
