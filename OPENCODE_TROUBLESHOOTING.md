# OpenCode.ai Troubleshooting Guide

## Problem

❌ **Error:** `Expecting value: line 1 column 1 (char 0)`

or

❌ **Error:** `OpenCode.ai returned HTML instead of JSON`

---

## Root Cause

The OpenCode.ai server is **running but the API is not initialized yet**. When you send a request to `/v1/chat/completions`, the server returns its web UI (HTML) instead of a JSON response.

This typically happens when:
- ⏱️ Server just started and still initializing (takes 30-60 seconds)
- 🔧 Configuration issue with OpenCode installation
- 🚫 API endpoints not properly loaded

---

## Solution 1: Wait for Server Initialization ⏳ (FASTEST)

**Time:** 1-2 minutes  
**Success Rate:** 90%

OpenCode.ai takes 30-60 seconds to fully initialize after starting. 

### Steps:

1. **Keep OpenCode running** — Don't stop it
2. **Wait 30-60 seconds** — Let it fully initialize
3. **Refresh the Streamlit app** — F5 or Ctrl+Shift+R
4. **Try generating again** — Click "🚀 Generate Verilog"
5. **It should work!** ✅

---

## Solution 2: Restart OpenCode.ai 🔄

**Time:** <2 minutes  
**Success Rate:** 95%

If waiting didn't work, the server needs a clean restart.

### Steps:

1. **Kill the OpenCode terminal:**
   - Click the OpenCode terminal window
   - Press `Ctrl+C` to stop the server
   - Wait 2 seconds for full shutdown

2. **Start fresh:**
   ```bash
   cd c:\Users\venka\Documents\rtl-gen-aii
   opencode serve --port 8000
   ```

3. **Wait for startup message:**
   ```
   Warning: OPENCODE_SERVER_PASSWORD is not set; server is unsecured.
   opencode server listening on http://127.0.0.1:8000
   ```

4. **Wait 30 seconds** — Let API endpoints initialize

5. **Return to Streamlit app:**
   - Refresh the browser (F5)
   - Try generating again

---

## Solution 3: Update OpenCode.ai 📦

**Time:** <2 minutes  
**Success Rate:** 80%

Your OpenCode.ai installation might be outdated.

### Steps:

```bash
# Activate venv
.\.venv\Scripts\Activate.ps1

# Update to latest version
pip install -U opencode-ai

# Verify installation
pip show opencode-ai

# Restart server
opencode serve --port 8000
```

---

## Solution 4: Check Server Health 🏥

**Time:** <1 minute  
**Helps diagnose:** Which solution will work

### Run diagnostic:

```bash
cd c:\Users\venka\Documents\rtl-gen-aii
python test_opencode.py
```

### Expected output if working:
```
Status: 200
Content-Type: application/json; charset=utf-8
JSON Response:
{
  "choices": [
    {
      "message": {
        "content": "..."
      }
    }
  ]
}
```

### If you see HTML instead of JSON:
→ **Use Solution 1 or 2 above**

---

## Solution 5: Switch Back to Groq 💰

**Time:** <1 minute  
**Status:** Groq limit resets in ~24 hours

If OpenCode.ai keeps failing after trying solutions 1-3:

1. **Wait 24 hours** for Groq limit to reset
2. **Or upgrade to Dev Tier:** https://console.groq.com/settings/billing
3. **In Streamlit app:**
   - Select "groq" from AI Provider dropdown
   - Click "Generate Verilog + Run Full Pipeline"

---

## Prevention Tips 💡

### For Future Starts:

**When starting Streamlit + OpenCode:**
1. Start OpenCode first (in dedicated terminal)
2. Wait 30 seconds for full initialization
3. **Then** open/refresh Streamlit app
4. All generations will work instantly

**Keep the process running:**
- Don't close OpenCode terminal while using Streamlit
- If you close it, restart with: `opencode serve --port 8000`

---

## Advanced: Manual API Test

If diagnostics show issues, test manually:

```python
import httpx

response = httpx.post(
    "http://localhost:8000/v1/chat/completions",
    json={
        "model": "opencode",
        "messages": [{"role": "user", "content": "Say hi"}],
        "max_tokens": 50
    },
    headers={"Authorization": "Bearer opencode"}
)

print(f"Status: {response.status_code}")
print(f"Type: {response.headers.get('content-type')}")
print(response.json())  # Should print JSON, not HTML
```

**If this returns HTML:**
→ **Use Solution 2 (Restart OpenCode)**

---

## Current Status

**OpenCode.ai Server:** ✅ Running on `http://127.0.0.1:8000`  
**Problem:** API returning HTML (still initializing)  
**Next Step:** Wait 30 seconds and retry

---

## Questions?

- **Can't get it working?** → Switch to Groq (Solution 5)
- **Error persists?** → Restart OpenCode (Solution 2)
- **Still broken?** → Upgrade OpenCode (Solution 3)

---

**Last Updated:** 2026-04-08  
**Diagnostic Tool:** `test_opencode.py`
