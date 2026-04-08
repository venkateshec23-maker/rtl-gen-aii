# Groq Rate Limit — Solutions Guide

## Problem
❌ **Error:** `Rate limit exceeded for model llama-3.3-70b-versatile`

Your Groq free tier has hit the **daily token limit**: 100,000 tokens/day
- **Used:** 98,832 tokens
- **Limit:** 100,000 tokens
- **Need to wait:** ~52 minutes before limit resets (or upgrade)

---

## Solution 1: Wait for Limit Reset ⏳
**Time:** ~24 hours  
**Cost:** Free  
**Effort:** None

The daily limit automatically resets every 24 hours. You can try again tomorrow.

---

## Solution 2: Use OpenCode.ai Locally 🚀 (RECOMMENDED)
**Time:** ~5 minutes  
**Cost:** Free  
**Effort:** Medium

OpenCode.ai is a local AI agent with **unlimited tokens** when running on your machine.

### Setup Steps:

1. **Install OpenCode.ai:**
   ```bash
   pip install opencode-ai
   ```

2. **Start the OpenCode.ai server:**
   ```bash
   opencode serve --port 8000
   ```
   
   Keep this terminal running in the background.

3. **Switch provider in Streamlit app:**
   - Reload the app: https://rtl-gen-aii-owmrc8vwmb2oygspt4w4jj.streamlit.app/
   - In the "AI Provider" dropdown, select **"opencode"**
   - Click "Generate Verilog + Run Full Pipeline"

4. **Done!** The app now uses local OpenCode.ai with unlimited tokens.

---

## Solution 3: Upgrade Groq to Dev Tier 💰
**Time:** ~5 minutes  
**Cost:** Varies (free tier → paid)  
**Effort:** Low

### Upgrade Steps:

1. **Go to Groq Console:**
   - https://console.groq.com/settings/billing

2. **Click "Upgrade to Dev Tier"**
   - Dev Tier: $0.10 per million input tokens
   - Higher daily limits (e.g., 500K+ tokens/day)
   - Better for production use

3. **Update your API key:**
   - Your old free-tier key still works with Dev Tier!
   - No code changes needed
   - Just wait ~5 minutes for upgrade to activate

4. **Start generating again!**

---

## Solution 4: Use a Private API Key 🔑
**Time:** <1 minute  
**Cost:** Depends on key plan  
**Effort:** Low

If you have a personal Groq API key with higher limits:

### Local Development:
```bash
# In PowerShell
$env:GROQ_API_KEY = "your-private-api-key-here"

# Run app
streamlit run app.py
```

### Streamlit Cloud:
1. Go to app settings: https://share.streamlit.io/apps
2. Click your app → Settings
3. Add secret: `GROQ_API_KEY = your-private-api-key-here`
4. Save and redeploy

---

## Recommended Path 🎯

**For Local Development (Right Now):**
→ **Use OpenCode.ai** (Solution 2)
- No limits
- Instant setup
- Full control

**For Production/Long-term:**
→ **Upgrade Groq to Dev Tier** (Solution 3)
- Unlimited tokens
- Cloud-hosted
- Scales with your needs

---

## Testing Your Fix

After implementing a solution:

1. **Go to app:** https://rtl-gen-aii-owmrc8vwmb2oygspt4w4jj.streamlit.app/

2. **Or run locally:**
   ```bash
   streamlit run app.py
   ```

3. **Select provider and try generating:**
   - Example: "Design a 4-bit adder"
   - Should complete without rate limit error

---

## Current API Key Status

**Free Tier API Key:** (Check environment variable `GROQ_API_KEY`)
- Status: **Rate limit exceeded (98,832/100,000 tokens used)**
- Reset: ~24 hours (automatically resets at UTC midnight or per billing period)
- Action: See solutions above

---

## Questions?

Check these resources:
- **Groq Docs:** https://console.groq.com/docs
- **OpenCode.ai Docs:** https://docs.opencode.ai/
- **RTL-Gen AII Docs:** See README.md

---

**Last Updated:** 2026-04-08  
**Lines of Code:** Updated error handling (34794bf)
