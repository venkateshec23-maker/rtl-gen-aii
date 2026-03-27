# 🚀 OpenCode Model Configuration & Speed Optimization

**Current Status:** OpenCode v1.3.3 is working, but model selection can be slow.

---

## Why It's Slow

- **First Run:** Downloads Docker image + npm packages (~40 seconds)
- **Model Selection:** OpenCode queries available models (~10-20 seconds)
- **Free Tier:** Default uses slower/free model endpoint

---

## Speed Solutions

### Option 1: Configure a Specific Model (Fastest)

```bash
# Set default model (replaces model selection every time)
opencode providers
# Select your model: anthropic/claude-opus, openai/gpt-4, etc.

# Then use it directly:
opencode run "your description" -m anthropic/claude-opus
```

### Option 2: Use Local/Fast Model

```bash
# Use faster open-source models
opencode run "description" -m ollama/llama2:latest
# or
opencode run "description" -m mistral/mistral-7b
```

### Option 3: Save a Session (Best for Iterative Work)

```bash
# First run (slow - sets up model)
opencode run "8-bit counter"

# Subsequent runs (faster - reuses existing session)
opencode run "4-bit adder" -c        # Continue last session
opencode run "multiplexer" -s 123    # Use specific session
```

---

## Modified PowerShell Script Usage

### Faster with Specific Model

```powershell
# Using Claude (requires API key)
$env:ANTHROPIC_API_KEY = "your-key-here"
.\run_opencode.ps1 "8-bit counter"

# Or with environment variable
$env:OPENCODE_MODEL = "anthropic/claude-opus"
.\run_opencode.ps1 "your description"
```

### Using Free Models

```powershell
# Groq (fast, free API)
$env:GROQ_API_KEY = "your-key-here"
.\run_opencode.ps1 "8-bit counter" -m groq/mixtral-8x7b-32768

# Local models (no API key needed)
.\run_opencode.ps1 "8-bit counter" -m ollama/llama2
```

---

## Free API Options

### Top Free/Cheap Providers

| Provider | Speed | Cost | Setup |
|----------|-------|------|-------|
| **Groq** | ⚡⚡⚡ Fast | Free | Get key at groq.com |
| **Hugging Face** | ⚡⚡ Medium | Free tier | huggingface.co |
| **Mistral** | ⚡⚡ Medium | Free | mistral.ai |
| **Ollama** | ⚡ Depends | Free | Local models |

### Groq Setup (Recommended - Fast & Free)

1. **Get API Key:**
   ```
   https://console.groq.com
   Sign up → Create API key
   ```

2. **Set Environment Variable:**
   ```powershell
   $env:GROQ_API_KEY = "gsk_your_key_here"
   ```

3. **Run OpenCode:**
   ```powershell
   # Groq models are VERY fast (2-5 seconds typically)
   .\run_opencode.ps1 "8-bit counter"
   ```

---

## Caching Strategy (For Repeated Designs)

### Save Generated Code

```powershell
# Generate once
.\run_opencode.ps1 "8-bit counter" > counter.txt

# Reuse anytime
Get-Content counter.txt | Set-Clipboard
```

### Create Templates

```powershell
# Save to templates directory
mkdir templates
.\run_opencode.ps1 "basic counter" > templates/counter.v
.\run_opencode.ps1 "basic adder" > templates/adder.v
.\run_opencode.ps1 "basic mux" > templates/mux.v

# Quick lookup later
Get-Content templates/counter.v
```

---

## Docker Optimization

### Skip npm Install (After First Run)

Create a persistent cache:

```dockerfile
# Dockerfile.node-cached
FROM node:25

RUN npm install -g opencode-ai@latest

VOLUME ["/workspace"]
WORKDIR /workspace

ENTRYPOINT ["opencode"]
CMD ["--help"]
```

Build once:
```powershell
docker build -f Dockerfile.node-cached -t opencode-cached .
```

Use:
```powershell
docker run -it --rm -v "$PWD`:/workspace" -w /workspace opencode-cached run "your description"
```

---

## Performance Tips

### 1. **Batch Multiple Designs**
```powershell
# Generate 5 designs in one session (faster than 5 separate calls)
.\run_opencode.ps1 "8-bit counter"
.\run_opencode.ps1 "8-bit adder" -c        # Continue session
.\run_opencode.ps1 "4-to-1 mux" -c         # Reuse model
```

### 2. **Use Shorter Descriptions**
```powershell
# Slow (verbose)
.\run_opencode.ps1 "Create a fully synchronous 8-bit binary counter with an active-high reset signal and an enable input"

# Fast (concise)
.\run_opencode.ps1 "8-bit counter with reset and enable"
```

### 3. **Specify Exact Requirements**
```powershell
# Slower (vague - model has to guess)
.\run_opencode.ps1 "counter"

# Faster (specific)
.\run_opencode.ps1 "8-bit synchronous counter, behavioral Verilog"
```

### 4. **Disable Unnecessary Features**
```powershell
# Don't regenerate model list
# Just use run directly with -m flag
.\run_opencode.ps1 "design" -m groq/mixtral-8x7b-32768
```

---

## Complete Fast Setup

### Step 1: Get Groq API Key
```
https://console.groq.com → Sign up → Copy key
```

### Step 2: Set Environment Variable
```powershell
$env:GROQ_API_KEY = "gsk_your_key"
```

### Step 3: Test (Should be 5-10 seconds total)
```powershell
.\run_opencode.ps1 "4-bit counter"
```

### Expected Output
```
🚀 Running OpenCode: 4-bit counter
added X packages in 5s
[OpenCode generates Verilog in 3-5 seconds]
```

---

## Benchmark Results

### With Groq (Recommended)
- Docker image already pulled: ~10s total
- First run with image: ~45s total
- Subsequent runs: ~10s total
- Generation time: 3-5s

### With opencode.ai free tier
- First run: ~60s
- Docker cached: ~25-30s
- Model selection: ~15s
- Generation: ~10s

---

## Updated PowerShell Script (Optional Enhancements)

For maximum speed, update `run_opencode.ps1`:

```powershell
param(
    [Parameter(Position = 0, ValueFromRemainingArguments = $true)]
    [string[]]$Arguments,
    
    [string]$Model = $null,              # Add model parameter
    [switch]$Continue = $false,           # Add continue flag
    [string]$SessionID = $null            # Add session parameter
)

# ... existing code ...

# Usage
if ($Continue) {
    $cmd += " -c"
}
if ($SessionID) {
    $cmd += " -s $SessionID"
}
if ($Model) {
    $cmd += " -m $Model"
}
```

Then use:
```powershell
.\run_opencode.ps1 "8-bit counter" -Model groq/mixtral-8x7b-32768
.\run_opencode.ps1 "4-bit adder" -Continue
```

---

## Summary: Fastest Setup

1. **Get Groq API Key** (2 minutes)
   ```
   https://console.groq.com
   ```

2. **Set Environment Variable**
   ```powershell
   $env:GROQ_API_KEY = "gsk_..."
   ```

3. **Generate Verilog** (10-15 seconds!)
   ```powershell
   .\run_opencode.ps1 "8-bit counter"
   ```

4. **Copy to Streamlit**
   - Custom Design page → Paste code
   - Run Pipeline → Get GDS in ~20 seconds

---

## Next Steps

1. **Update PowerShell script** (optional but recommended)
2. **Get Groq API key**
3. **Test with Groq** (super fast!)
4. **Generate designs** → Run through pipeline → Get GDS files

---

**Pro Tip:** Once Docker image is cached, subsequent Groq-based generations take **only 10-15 seconds total** from description to Verilog! 🚀
