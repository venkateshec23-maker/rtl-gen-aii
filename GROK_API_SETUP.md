# 🚀 GitHub Actions Setup: Using Grok API

**You have**: Grok API key (gsk_... - your actual key)  
**Goal**: Deploy RTL-Gen AI with Grok instead of Claude  
**Time**: 5 minutes

---

## ⚡ Quick Setup (3 Steps)

### Step 1: Add Grok Secret to GitHub (2 min)

Go to: **GitHub Repo → Settings → Secrets and variables → Actions**

Click: **New repository secret**

```
Name:  GROK_API_KEY
Value: gsk_... (your Grok key)

Click: Add secret
```

✅ You should see it listed with ●●●●●● covering the value

### Step 2: Update Config (1 min)

The config.json is already updated to use Grok as default. ✓

**Verify** [config.json](config.json) shows:
```json
"default_provider": "grok"
```

### Step 3: Deploy! (1 min)

```bash
git add .
git commit -m "Deploy: Using Grok API"
git push origin main
```

**Done!** 🎉 Your app will deploy with Grok in ~8-10 minutes.

---

## 📊 What Happens

```
Your git push
    ↓
GitHub Actions triggers
    ↓
1. Tests run
2. Docker builds
3. Reads GROK_API_KEY from your secret
4. Starts RTL-Gen AI with Grok as LLM
5. Deploys to cloud
    ↓
YOUR APP USES GROK! ✅
```

---

## ✅ Verification

**After deployment:**

1. Open your app URL
2. Go to "RTL Generation" tab
3. Enter a prompt: "Generate a 4-bit adder"
4. Click "Generate with Grok"
5. See RTL code generated using Grok! ✨

---

## 🔧 Alternative Providers

If you want to switch providers later:

```json
// In config.json, set one to "enabled": true

"grok": {
  "enabled": true    ← Uses Grok
}

"anthropic": {
  "enabled": false
}

"deepseek": {
  "enabled": false
}
```

---

## 📋 Complete Secret Setup (All Options)

### Required
```
Name: GROK_API_KEY
Value: gsk_... (your Grok key)
```

### Optional - For AWS
```
Name: AWS_ACCOUNT_ID
Value: 123456789012
```

### Optional - For DigitalOcean
```
Name: DIGITALOCEAN_ACCESS_TOKEN
Value: dop_v1_...
```

---

## 🚀 Deploy Now!

```bash
git push origin main
# Watch: GitHub → Actions tab
# Time: 8-10 minutes
# Result: LIVE with Grok! 🎉
```

---

## 📚 Need More Help?

- **Quick Ref**: [GITHUB_ACTIONS_QUICKREF.md](GITHUB_ACTIONS_QUICKREF.md)
- **Step by Step**: [GITHUB_ACTIONS_STEP_BY_STEP.md](GITHUB_ACTIONS_STEP_BY_STEP.md)
- **Full Guide**: [GITHUB_ACTIONS_SETUP.md](GITHUB_ACTIONS_SETUP.md)
- **All Guides**: [DEPLOYMENT_DOCUMENTATION.md](DEPLOYMENT_DOCUMENTATION.md)

---

**Your Grok-powered RTL-Gen AI is ready!** 🚀

Just push to GitHub and let GitHub Actions do the rest.
