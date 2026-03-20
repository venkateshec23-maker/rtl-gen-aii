# 🚀 GitHub Actions Automated Deployment: Step-by-Step

**Status**: Ready to Deploy  
**Time to Deploy**: 13-15 minutes total (5 min setup + 8-10 min deploy)

---

## 📋 What You'll Do

1. **Get credentials** (2 min) - Gather API keys
2. **Add GitHub Secrets** (2 min) - Store credentials securely
3. **Push code** (1 min) - Trigger deployment
4. **Watch it deploy** (8-10 min) - Monitor progress
5. **It's LIVE!** ✅ - Your app is in production

---

## 🎯 Step 1: Get Your Credentials (2 minutes)

### 📝 Copy These Values

```
You need ONE of:
├─ Anthropic API Key (REQUIRED)
│  From: https://console.anthropic.com/
│  Format: sk-ant-v0-...
│
└─ Grok API Key (REQUIRED - xAI)
   From: https://console.grok.com/
   Format: gsk_U64Mi...

Plus OPTIONAL:
├─ AWS Account ID
│  From: AWS Console → Account
│  Format: 123456789012 (12 digits)
│
└─ DigitalOcean Token
   From: https://cloud.digitalocean.com/account/api/tokens
   Format: dop_v1_...
```

**Where to Find Each:**

#### Anthropic API Key
```
From: https://console.anthropic.com/
1. Sign in with your account
2. Left sidebar: Click "API keys"
3. Click "Create Key"
4. Copy the key (starts with "sk-")
5. Keep in notepad for next step
```

#### Grok API Key
```
From: https://console.grok.com/ (or xAI console)
1. Sign in with your account
2. Navigate to API keys section
3. Click "Create New"
4. Copy the key (starts with "gsk_")
5. Keep in notepad for next step
```

(Use ONE of the above - Anthropic OR Grok)

#### AWS Account ID (Optional)
```
1. Visit: https://console.aws.amazon.com/
2. Click account dropdown (top-right)
3. Click "My Account"
4. Find "Account ID" (12 digits)
5. Copy it to notepad
```

#### DigitalOcean Token (Optional)
```
1. Visit: https://cloud.digitalocean.com/account/api/tokens
2. Click "Generate New Token"
3. Name it: "GitHub-Actions"
4. Select "Full access"
5. Click Generate
6. COPY IMMEDIATELY (shown only once!)
7. Save to notepad
```

---

## 🔐 Step 2: Add GitHub Secrets (2 minutes)

### Navigate to Secrets
```
1. Go to: https://github.com/YOUR_USERNAME/rtl-gen-aii
2. Click: Settings tab
3. Left sidebar: Secrets and variables → Actions
4. Button: "New repository secret"
```

### Add Secret #1: LLM API Key (Choose One)

**Using Claude:**
```
Name:  ANTHROPIC_API_KEY
Value: sk-ant-v0-...    (paste your Anthropic key)

Click: Add secret
```

**Using Grok:**
```
Name:  GROK_API_KEY
Value: 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    (paste your Grok key)

Click: Add secret
```

### Add Secret #2: AWS_ACCOUNT_ID (OPTIONAL)

```
Only if you want AWS deployment!

Name:  AWS_ACCOUNT_ID
Value: 123456789012     (your 12-digit ID)

Click: Add secret
```

### Add Secret #3: DIGITALOCEAN_ACCESS_TOKEN (OPTIONAL)

```
Only if you want DigitalOcean deployment!

Name:  DIGITALOCEAN_ACCESS_TOKEN
Value: dop_v1_...       (your token)

Click: Add secret
```

### Verify All Secrets Added

```
You should see:
✓ ANTHROPIC_API_KEY (if using Claude) OR
✓ GROK_API_KEY (if using Grok)         (green checkmark)
✓ AWS_ACCOUNT_ID             (green checkmark) [optional]
✓ DIGITALOCEAN_ACCESS_TOKEN  (green checkmark) [optional]
```

---

## ⚡ Step 3: Push Your Code (1 minute)

### Command to Deploy

```bash
# Navigate to your repo
cd rtl-gen-aii

# Stage all changes
git add .

# Commit with message
git commit -m "Deploy: Automated cloud setup"

# Push to GitHub
git push origin main
```

**That's it!** 🎉 Deployment starts automatically.

---

## 📊 Step 4: Watch Deployment (8-10 minutes)

### View Progress

```
1. Go to: https://github.com/YOUR_USERNAME/rtl-gen-aii
2. Click: Actions tab
3. Click: "Deploy RTL-Gen AI" workflow
4. Watch each step complete:
```

### Expected Timeline

```
RUNNING TESTS
├─ Test: Python 3.11          ⏳ ~2 min → ✅
├─ Test: Python 3.12          ⏳ ~2 min → ✅
├─ Lint: flake8               ⏳ ~1 min → ✅
└─ Coverage Upload            ⏳ ~1 min → ✅

BUILDING & DEPLOYING
├─ Build Docker Image         ⏳ ~3-5 min → ✅
├─ Push to AWS ECR            ⏳ ~1 min → ✅
├─ Update AWS ECS             ⏳ ~2 min → ✅
└─ Deploy DigitalOcean        ⏳ ~2 min → ✅

TOTAL TIME: ~8-10 minutes
```

### Success Indicators

```
✅ All tests pass (green check)
✅ Lint succeeds (no warnings)
✅ Docker builds (no errors)
✅ Deploy completes (green check)

Final Status: ✅ workflow completed successfully
```

---

## 🎊 Step 5: It's LIVE! (Your App is Running)

### Get Your URLs

**If deployed to DigitalOcean:**
```
1. Go to: https://cloud.digitalocean.com/apps
2. Find: Your app (rtl-gen-ai or similar)
3. Click it
4. Copy URL from "Live App" section
5. Example: https://rtl-gen-ai-abc123.ondigitalocean.app
```

**If deployed to AWS:**
```
1. Go to: https://console.aws.amazon.com/ecs/
2. Find: rtl-gen-cluster
3. Find: rtl-gen-service
4. Check: Load Balancer URL
5. Example: http://rtl-gen-alb-123.us-east-1.elb.amazonaws.com
```

### Test Your App

```
1. Open your URL in browser
2. You should see: Streamlit interface
3. Try generating an RTL design:
   - Tab 1: Enter prompt
   - Click: Generate
   - See: RTL code generated
4. Success! ✅
```

---

## 🔄 Next Time You Update

### Simple Workflow

```bash
# Make changes to code
# Edit app.py or python files
# ...your edits here...

# Deploy automatically
git add .
git commit -m "Feature: Your feature name"
git push origin main

# GitHub Actions automatically:
# 1. Runs tests
# 2. Builds Docker image
# 3. Pushes to cloud
# 4. Updates production
# 5. Your app is updated! ✅

# Time: ~8-10 minutes
```

### Watch Progress

```
1. Click Actions tab
2. See workflow running
3. Each step completes
4. When green checkmark appears - you're live!
```

---

## 🐛 Troubleshooting Quick Guide

### Tests Failing?

```
Error: "pytest failed"
Solution:
1. Run locally: pytest tests/
2. Fix errors in code
3. git push again
4. GitHub Actions will retry
```

### Build Failing?

```
Error: "Docker build error"
Solution:
1. Run locally: docker build -t rtl-gen-ai:latest .
2. Check Dockerfile syntax
3. Check requirements.txt
4. Fix and push again
```

### Secrets Not Found?

```
Error: "ANTHROPIC_API_KEY not found"
Solution:
1. Check secret spelling (case-sensitive!)
2. Verify it's in Settings → Secrets
3. Wait 10 seconds after adding
4. Trigger new workflow with git push
```

### Deployment Skipped?

```
Error: Workflow runs but doesn't deploy
Solution:
1. Check if DIGITALOCEAN_ACCESS_TOKEN is set
2. Check if AWS credentials configured
3. At least ANTHROPIC_API_KEY is required
4. Set the secret and push again
```

### App Not Accessible?

```
Error: Can't reach app URL
Solution - DigitalOcean:
  doctl apps list  # Check status (should be "active")
  
Solution - AWS:
  aws ecs describe-services --cluster rtl-gen-cluster-prod --services rtl-gen-service-prod
  # Check DesiredCount matches RunningCount
```

---

## ✅ Verification Checklist

Before pushing:
- [ ] All secrets added to GitHub
- [ ] Code changes committed locally
- [ ] Ready to push

During deployment:
- [ ] Watch Actions tab
- [ ] Each step completes (green checks)
- [ ] No red X marks
- [ ] Total time ~8-10 minutes

After deployment:
- [ ] App URL is accessible
- [ ] Can sign in / use app
- [ ] Features work correctly
- [ ] No errors in logs

---

## 📈 Monitoring Your Deployment

### View Logs

**GitHub Actions Logs:**
```
1. Actions tab
2. Click workflow name
3. Click "Deploy" job
4. Scroll to see all steps
5. Each step shows output
```

**Application Logs:**

**DigitalOcean:**
```
doctl apps logs <app-id>
# Real-time streaming logs
# Shows app errors/messages
```

**AWS:**
```
aws logs tail /ecs/rtl-gen-prod --follow
# Real-time streaming logs
# Shows container output
```

---

## 🎯 Common Tasks

### Rollback to Previous Version

```bash
git log --oneline        # See previous commits
git revert <commit-id>   # Revert specific commit
git push origin main     # Deploy reverted version
# GitHub Actions redeploys automatically!
```

### Disable Certain Deployments

```yaml
# In .github/workflows/deploy.yml, comment out:
# - name: Deploy to AWS ECS
# - name: Deploy to DigitalOcean
# Then only ANTHROPIC_API_KEY is required
```

### Manually Trigger Workflow

```
1. Actions tab
2. Left sidebar: Select workflow
3. Button: "Run workflow"
4. Select branch: main
5. Click "Run workflow"
# Deploys even without git push
```

---

## 💡 Pro Tips

1. **Write good commit messages** - Shows up in Actions history
2. **Keep master branch stable** - Tests run on every push
3. **Use git branches for development** - Merge to main when ready
4. **Check Actions tab regularly** - Stay informed about deployments
5. **Monitor costs monthly** - Set calendar reminder

---

## 🚀 You're Ready!

Everything is set up. Here's your complete workflow:

```
┌─ Update code locally
│  └─ git add . && git commit -m "Feature X"
│     └─ git push origin main
│         └─ GitHub Actions triggers automatically
│           ├─ Tests run (~1-2 min)
│           ├─ Build Docker (~3-5 min)
│           ├─ Deploy to clouds (~2-3 min)
│           └─ YOUR APP IS LIVE! ✅
└─ Watch progress in Actions tab
```

---

## 📞 Next Steps

1. ✅ Get credentials (2 min)
2. ✅ Add GitHub Secrets (2 min)
3. ✅ Push code to GitHub (1 min)
4. ✅ Watch Actions for deployment (8-10 min)
5. ✅ Your app is live!
6. ✅ Share your URL! 🎉

---

## 📚 Additional Resources

For more details, see:
- [GITHUB_ACTIONS_SETUP.md](GITHUB_ACTIONS_SETUP.md) - Complete setup guide
- [GITHUB_ACTIONS_QUICKREF.md](GITHUB_ACTIONS_QUICKREF.md) - Quick reference
- [DEPLOYMENT_DOCUMENTATION.md](DEPLOYMENT_DOCUMENTATION.md) - All guides
- [CLOUD_DEPLOYMENT_QUICKSTART.md](CLOUD_DEPLOYMENT_QUICKSTART.md) - Quick start

---

**Ready to deploy?** 🚀

Start with **Step 1** above and follow each step. 

**You'll be live in 15 minutes!**

*Happy deploying!* 🎉
