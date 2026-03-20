# 🚀 GitHub Actions: Quick Start (5 Minutes)

---

## 🎯 What You Need (3 Things)

| Item | Where to Get | Example |
|------|--------------|---------|
| **LLM API Key** | Anthropic OR Grok | sk-ant-v0-abc... OR gsk_U64Mi... |
| **AWS Account ID** | AWS Console → Account | 123456789012 |
| **DO Token** (optional) | https://cloud.digitalocean.com/account/api/tokens | dop_v1_abc... |

**Using Grok?** Use `GROK_API_KEY` instead of `ANTHROPIC_API_KEY`

---

## ⚡ Setup (5 Minutes)

### 1. Add Secrets to GitHub (2 minutes)
```
GitHub Repo → Settings → Secrets and variables → Actions → New secret

SECRET 1 - Choose One:

Option A (Claude):
Name: ANTHROPIC_API_KEY
Value: sk-ant-...

Option B (Grok):
Name: GROK_API_KEY
Value: gsk_... (your Grok key)

SECRET 2 (optional):
Name: AWS_ACCOUNT_ID
Value: 123456789012

SECRET 3 (optional):
Name: DIGITALOCEAN_ACCESS_TOKEN
Value: dop_v1_...

✓ Click "Add secret" for each
```

### 2. Push Your Code (1 minute)
```bash
git add .
git commit -m "Deploy: Cloud setup"
git push origin main
```

### 3. Watch It Deploy (2 minutes)
```
GitHub → Actions tab → See "Deploy RTL-Gen AI" running
Total time: ~8-10 minutes
```

---

## ✅ Success Looks Like

```
✓ Test: Python 3.11
✓ Test: Python 3.12
✓ Lint: flake8
✓ Build: Docker image
✓ Push: to AWS ECR
✓ Deploy: AWS ECS updated
✓ Deploy: DigitalOcean ready

Status: ✅ All jobs passed!
```

---

## 🔄 Next Time You Push

```bash
# Edit code
git push origin main

# Automatically:
# 1. Runs tests
# 2. Builds Docker image
# 3. Pushes to cloud
# 4. Updates production
# 5. APP LIVE! ✅
```

---

## 📊 Monitor Live Deployment

```
Go to: GitHub Repo → Actions tab
Watch progress:
  ⏳ Tests running...
  ⏳ Building Docker...
  ⏳ Deploying...
  ✅ LIVE!
```

---

## 🆘 If Something Fails

| Error | Fix |
|-------|-----|
| **Secret not found** | Check name spelling (case-sensitive) |
| **Tests failing** | Run `pytest tests/` locally first |
| **Docker build error** | Run `docker build .` locally |
| **AWS deploy fails** | Verify AWS_ACCOUNT_ID is 12 digits |
| **DO deploy skipped** | Optional - set DIGITALOCEAN_ACCESS_TOKEN if desired |

---

## 💡 Key Points

✨ **Automatic**: No manual steps needed  
✨ **Fast**: ~8-10 minutes per deployment  
✨ **Safe**: Tests run before deploy  
✨ **Easy**: Just `git push` and done  
✨ **Monitored**: See progress in Actions tab  

---

## 📚 Full Details

For complete setup guide, see: [GITHUB_ACTIONS_SETUP.md](GITHUB_ACTIONS_SETUP.md)

---

**Ready? Just push!** 🚀

```bash
git push origin main
# Watch Actions tab for live deployment
```
