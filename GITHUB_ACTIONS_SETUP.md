# GitHub Actions Setup: Fully Automated Deployment

**Goal**: Auto-deploy RTL-Gen AI on every push to `main` branch

---

## 📋 Prerequisites

1. Code pushed to GitHub repository
2. GitHub account (free tier works!)
3. DigitalOcean and AWS credentials ready

---

## 🔑 Step 1: Generate Required Tokens

### A. LLM API Key (Required) - Choose One
```
Option 1: Anthropic Claude
├─ Go to: https://console.anthropic.com/
├─ Click "API keys" in left sidebar
├─ Click "Create Key"
├─ Copy the key (starts with "sk-ant-")
└─ Keep it secret - save for next step

Option 2: Grok (xAI)
├─ Go to: https://console.grok.com/ (or xAI console)
├─ Navigate to API keys
├─ Create new key
├─ Copy the key (starts with "gsk_")
└─ Keep it secret - save for next step
```

### B. AWS Account ID (For AWS deployment)
```
1. Go to: https://console.aws.amazon.com/
2. Click account name (top-right) → My Account
3. Copy "Account ID" (12 digits)
4. Example: 123456789012
```

### C. DigitalOcean Access Token (For DO deployment)
```
1. Go to: https://cloud.digitalocean.com/account/api/tokens
2. Click "Generate New Token"
3. Name it: "RTL-Gen-AI-GitHub"
4. Select scope: "Full access"
5. Click Generate
6. Copy token immediately (shown only once!)
```

---

## 🔐 Step 2: Add GitHub Secrets

### Find Settings
```
1. Go to GitHub repository
2. Click "Settings" tab
3. Left sidebar: "Secrets and variables" → "Actions"
4. Click "New repository secret"
```

### Add Each Secret

#### Secret 1: LLM API Key (Choose One)

**Option A: Anthropic Claude**
```
Name: ANTHROPIC_API_KEY
Value: sk-...   (from Step 1.A)
Click: Add secret
```

**Option B: Grok**
```
Name: GROK_API_KEY
Value: gsk_...   (from Step 1.A)
Click: Add secret
```

#### Secret 2: AWS_ACCOUNT_ID (Optional - for AWS deployment)
```
Name: AWS_ACCOUNT_ID
Value: 123456789012   (from Step 1.B)
Click: Add secret
```

#### Secret 3: DIGITALOCEAN_ACCESS_TOKEN (Optional - for DO deployment)
```
Name: DIGITALOCEAN_ACCESS_TOKEN
Value: dop_v1_...   (from Step 1.C)
Click: Add secret
```

**Result**: You should see all secrets listed (values hidden with ●●●)

Required:
- [ ] ANTHROPIC_API_KEY OR GROK_API_KEY (one of these required)

Optional:
- [ ] AWS_ACCOUNT_ID
- [ ] DIGITALOCEAN_ACCESS_TOKEN

---

## 🚀 Step 3: Trigger First Deployment

### Option A: Push Code
```bash
cd rtl-gen-aii
git add .
git commit -m "Deploy: Initial cloud setup"
git push origin main
```

### Option B: Manual Trigger (if supported)
```
1. Go to GitHub repo
2. Click "Actions" tab
3. Select "Deploy RTL-Gen AI"
4. Click "Run workflow"
5. Select branch: "main"
6. Click "Run workflow"
```

---

## 📊 Step 4: Monitor Deployment

### Watch in GitHub Actions

```
1. Go to GitHub repo
2. Click "Actions" tab
3. You'll see "Deploy RTL-Gen AI" workflow running
4. Click on it to see progress
5. Each job shows:
   ✓ Test (Python 3.11)
   ✓ Test (Python 3.12)
   ✓ Build (Docker image)
   ✓ Deploy (AWS/DigitalOcean)
```

### Expected Timeline
- **Tests**: 2-3 minutes
- **Build**: 3-5 minutes
- **Deploy**: 2-3 minutes
- **Total**: ~8-10 minutes

### Success Indicators
```
✅ All tests passed
✅ Docker image built
✅ Image pushed to ECR
✅ ECS service updated (if AWS)
✅ App deployed (if DigitalOcean)
```

---

## 🐛 Troubleshooting

### Workflow doesn't appear?
```bash
❌ Problem: Can't find "Deploy RTL-Gen AI" workflow
✅ Solution: 
   - Ensure file: .github/workflows/deploy.yml exists
   - Wait 1-2 minutes after first push
   - Refresh Actions tab
```

### Tests failing?
```bash
❌ Problem: "pytest failed" in Actions log
✅ Solution:
   - Check log details
   - Run locally: pytest tests/
   - Fix errors, push again
```

### Secrets not recognized?
```bash
❌ Problem: "ANTHROPIC_API_KEY not found"
✅ Solution:
   - Verify secret name matches EXACTLY
   - Secrets are case-sensitive
   - After adding, wait ~10 seconds
```

### Build fails?
```bash
❌ Problem: Docker build error
✅ Solution:
   - Check Dockerfile syntax
   - Verify requirements.txt has all packages
   - Run locally: docker build -t rtl-gen-ai:latest .
```

### AWS deployment fails?
```bash
❌ Problem: "Invalid AWS credentials"
✅ Solution:
   - Verify AWS_ACCOUNT_ID is correct (12 digits)
   - Check ECR repository exists
   - Confirm AWS CLI configured locally
```

### DigitalOcean deployment fails?
```bash
❌ Problem: "doctl: not found" or authentication error
✅ Solution:
   - Verify DIGITALOCEAN_ACCESS_TOKEN is set
   - Token should start with "dop_v1_"
   - Check token has full access scope
```

---

## 📈 What Happens After Deployment

### Automatic
- ✅ New Docker image tagged with commit SHA
- ✅ AWS ECS service updated (pulls new image)
- ✅ Old containers gracefully shut down
- ✅ New containers start up
- ✅ Health checks verify success

### Manual Check
```bash
# Check Docker image
docker images

# For AWS - check ECS service
aws ecs describe-services --cluster rtl-gen-cluster --services rtl-gen-service

# For DigitalOcean - check app status
doctl apps get <app-id>
```

---

## 🔄 Workflow on Next Push

### Step 1: You make changes
```bash
# Edit app.py, add feature, fix bug
git add modified_files
git commit -m "Feature: Add new capability"
git push origin main
```

### Step 2: GitHub Actions runs
```
❯ Test                    (2-3 min)
❯ Lint                    (1 min)
❯ Build Docker image      (3-5 min)
❯ Push to ECR             (1 min)
❯ Update ECS service      (2 min)
❯ Deploy to DigitalOcean  (2 min)
```

### Step 3: Your app updates automatically
```
❯ New version running in production
❯ Users see latest features
❯ No manual deployment needed
❯ Zero downtime updates
```

---

## ✅ Verification Checklist

After first deployment:

- [ ] All GitHub secrets are set (green checkmarks)
- [ ] First workflow run completes successfully
- [ ] Docker image appears in ECR
- [ ] AWS ECS service shows new task
- [ ] DigitalOcean shows deploying/running
- [ ] App is accessible at public URL
- [ ] Database migrations complete
- [ ] Can generate RTL design in production

---

## 🎯 Common Deployment Scenarios

### Scenario 1: Bug Fix
```bash
git fix bug
git push origin main
# → Auto-deploys in 8-10 minutes
# → Production updated automatically
```

### Scenario 2: New Feature
```bash
git add feature
git push origin main
# → Tests run
# → Build succeeds
# → Deploy to staging (same config)
# → Ready for users
```

### Scenario 3: Database Migration
```bash
# Update python/database.py
git push origin main
# → New image built
# → ECS service updated
# → Migration runs on startup
# → Seamless upgrade
```

### Scenario 4: Rollback
```bash
git revert <commit-hash>
git push origin main
# → Triggers deployment of previous version
# → Takes ~8-10 minutes
# → Service restored
```

---

## 📊 Dashboard View

In GitHub Actions tab, you'll see:

```
✅ All workflows completed (green check)

Deploy RTL-Gen AI
├─ Test (Python 3.11)              ✅ Passed
├─ Test (Python 3.12)              ✅ Passed  
├─ Lint (flake8)                   ✅ Passed
├─ Build & Push Docker             ✅ 456 MB
├─ Update AWS ECS                  ✅ Deployed
└─ Deploy to DigitalOcean          ✅ Ready

Workflow completed in: 8m 42s
Triggered by: git push to main
```

---

## 🚀 Pro Tips

1. **Keep main branch stable** - Tests run on every push
2. **Use branches for development** - Merge to main when ready
3. **Check Actions tab regularly** - Monitor deployments
4. **Save logs for debugging** - Actions keeps 90-day history
5. **Update secrets annually** - Rotate credentials periodically

---

## 📚 Additional Resources

- GitHub Actions Docs: https://docs.github.com/en/actions
- Workflow Syntax: https://docs.github.com/en/actions/using-workflows/workflow-syntax-for-github-actions
- Secrets Management: https://docs.github.com/en/actions/security-guides/encrypted-secrets

---

## 🎉 You're All Set!

Now every push to `main` automatically:
- ✅ Tests your code
- ✅ Builds Docker image
- ✅ Deploys to cloud
- ✅ Updates production

**No manual deployment steps needed!** 🚀

---

*Next time you make a change, just:*
```bash
git push origin main
# And watch the magic happen in Actions tab!
```
