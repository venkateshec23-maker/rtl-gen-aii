# Azure Deployment Guide — Step-by-Step Setup

**Estimated Time**: 20-30 minutes

---

## 📋 Checklist Before Starting

- [ ] GitHub account (you have this)
- [ ] GitHub Edu Pack claimed (https://education.github.com/pack)
- [ ] Azure subscription (free from Edu Pack)
- [ ] `az` CLI installed (https://learn.microsoft.com/en-us/cli/azure/install-azure-cli-windows)

---

## 🎯 Phase 1: Azure Account Setup (5 min)

### 1.1 Create Azure Resource Group

```powershell
# Login to Azure (first time only)
az login

# Create resource group
az group create `
  --name rtl-gen-ai `
  --location eastus
```

**Output:**
```json
{
  "id": "/subscriptions/.../resourceGroups/rtl-gen-ai",
  "location": "eastus",
  "managedBy": null,
  "name": "rtl-gen-ai",
  "properties": { "provisioningState": "Succeeded" },
  "tags": {}
}
```

### 1.2 Create App Service Plan (Free Tier)

```powershell
az appservice plan create `
  --name rtl-gen-plan `
  --resource-group rtl-gen-ai `
  --sku FREE `
  --is-linux
```

**Output:**
```
Resource group: rtl-gen-ai
Name: rtl-gen-plan
Sku: Free (F1)
Location: eastus
```

### 1.3 Create Web App

```powershell
# Choose a unique name (use your name in it)
$APP_NAME = "rtl-gen-ai-$(Get-Random 1000 9999)"

az webapp create `
  --resource-group rtl-gen-ai `
  --plan rtl-gen-plan `
  --name $APP_NAME `
  --runtime "PYTHON|3.11"
```

**Save this value**: You'll need `$APP_NAME` later

---

## 🔑 Phase 2: Get Publish Profile (5 min)

### 2.1 Download Publish Profile

```powershell
# Get the publish profile
az webapp deployment profile show `
  --resource-group rtl-gen-ai `
  --name $APP_NAME > publishProfile.json

# Display it
Get-Content publishProfile.json
```

**Output**: XML with `<publishProfile>` tags containing credentials

### 2.2 View the Full Profile

If the file was large, view in parts:
```powershell
Get-Content publishProfile.json -Raw
```

Copy the **entire** XML content (from `<?xml...` to `</publishData>`)

---

## 🔐 Phase 3: GitHub Secrets Configuration (5 min)

### 3.1 Get Secret 1: App Name

```powershell
# This should be the $APP_NAME from Phase 1
Write-Host $APP_NAME
```

### 3.2 Get Secret 2: Publish Profile

```powershell
# Copy entire file content
Get-Content publishProfile.json -Raw | Set-Clipboard
```

### 3.3 Add to GitHub Secrets

1. Go to: https://github.com/venkateshec23-maker/rtl-gen-aii/settings/secrets/actions
2. Click **New repository secret**
3. **Add Secret #1:**
   - Name: `AZURE_APP_NAME`
   - Value: `rtl-gen-ai-xxxx` (your app name)
   - Click **Add secret**

4. **Add Secret #2:**
   - Name: `AZURE_PUBLISH_PROFILE`
   - Value: (paste XML from publishProfile.json)
   - Click **Add secret**

5. **Add Secret #3 (Optional but recommended):**
   - Name: `GROQ_API_KEY`
   - Value: `gsk_XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX` (your Groq API key from https://console.groq.com)
   - Click **Add secret**

**Verify:** You should see 3 secrets in the list

---

## 🚀 Phase 4: Test Deploy (5 min)

### 4.1 Trigger GitHub Actions

```powershell
# Make a small change to trigger deployment
echo "# Deployed to Azure" >> DEPLOYMENT_LOG.md

# Commit and push
git add DEPLOYMENT_LOG.md
git commit -m "Deploy to Azure"
git push origin main
```

### 4.2 Monitor Deployment

1. Go to: https://github.com/venkateshec23-maker/rtl-gen-aii/actions
2. Click the **Deploy to Azure** workflow run
3. Watch logs in real-time:
   - ✅ Setup Python
   - ✅ Install dependencies
   - ✅ Deploy to Azure

**Deployment should take 2-3 minutes**

### 4.3 Access Your App

```
https://{YOUR_APP_NAME}.azurewebsites.net
```

Replace `{YOUR_APP_NAME}` with the name from Phase 1

---

## 📊 Phase 5: Verification Checklist

- [ ] Azure app created (https://portal.azure.com)
- [ ] Publish profile downloaded
- [ ] GitHub secrets added (3 total)
- [ ] GitHub Actions workflow triggered
- [ ] Deployment logs show "Deployment successful"
- [ ] App accessible at Azure URL
- [ ] Streamlit dashboard loads
- [ ] AI Generator page works with Groq API key

---

## 🧪 Testing Deployed App

### 5.1 Test Basic Access

```powershell
# Replace with your Azure app name
$AZ_URL = "https://rtl-gen-ai-xxxx.azurewebsites.net"

# Should return HTML (Streamlit page)
Invoke-WebRequest $AZ_URL
```

### 5.2 Test AI Generator

1. Go to your Azure app URL
2. Navigate to: **🤖 AI Verilog Generator**
3. Try generating a 4-bit counter:
   - Name: `test_counter`
   - Description: `Simple 4-bit counter with clock and reset`
   - Design: Select from dropdown
4. Click **Generate Verilog**
5. Should see RTL + testbench generated

### 5.3 Check Logs

```powershell
# View Azure logs
az webapp log tail `
  --resource-group rtl-gen-ai `
  --name $APP_NAME
```

---

## 🎓 Optional: Custom Domain

### 6.1 Claim Free Domain from GitHub Edu Pack

1. Go to: https://education.github.com/pack
2. Find **Namecheap** offer
3. Claim (free .me domain for 1 year)

### 6.2 Point Domain to Azure

```powershell
# Add custom domain to Azure app
az webapp config hostname add `
  --resource-group rtl-gen-ai `
  --webapp-name $APP_NAME `
  --hostname your-domain.me

# Add SSL certificate
az webapp config ssl bind `
  --resource-group rtl-gen-ai `
  --webapp-name $APP_NAME `
  --certificate-thumbprint xxx \
  --ssl-type SNI
```

---

## ⚠️ Troubleshooting

### "Deployment failed in GitHub Actions"

Check logs:
```powershell
# View detailed workflow logs
# Go to: GitHub → Actions → Workflow run → Logs
```

Common issues:
- ❌ AZURE_PUBLISH_PROFILE not set → **Add to GitHub Secrets**
- ❌ GROQ_API_KEY invalid → **Update in GitHub Secrets**
- ❌ App name mismatch → **Verify AZURE_APP_NAME in secrets**

### "App returns 500 error"

```powershell
# Check Python version
az webapp config show `
  --resource-group rtl-gen-ai `
  --name $APP_NAME `
  --query pythonVersion

# Check logs
az webapp log download `
  --resource-group rtl-gen-ai `
  --name $APP_NAME `
  --log-file app-logs.zip
```

### "Streamlit not loading"

Azure runs on Linux. Verify:
```powershell
# Check runtime
az webapp config show `
  --resource-group rtl-gen-ai `
  --name $APP_NAME `
  --query linuxFxVersion
```

Should be: `PYTHON|3.11`

### "Port 8501 not accessible"

App Service runs on port 80. Web.config handles reverse proxy. Verify web.config exists in repo:
```powershell
# Should show web.config exists
git ls-files | grep web.config
```

---

## 📈 Monitoring & Scaling

### Monitor App Health

```powershell
# Get resource metrics
az monitor metrics list `
  --resource-group rtl-gen-ai `
  --resource-type "microsoft.web/sites" `
  --resource $APP_NAME `
  --metric "CpuTime,MemoryPercentage,Http5xx"
```

### Scale Up (If Needed)

```powershell
# Upgrade from Free to Standard (costs ~$10/month)
az appservice plan update `
  --name rtl-gen-plan `
  --resource-group rtl-gen-ai `
  --sku S1
```

---

## 🧹 Cleanup (If No Longer Needed)

```powershell
# Delete everything
az group delete `
  --name rtl-gen-ai `
  --yes
```

---

## 📞 Support

**If deployment fails:**
1. Check GitHub Actions logs
2. Check Azure app logs: `az webapp log tail ...`
3. Verify all secrets are set correctly
4. Create GitHub issue: https://github.com/venkateshec23-maker/rtl-gen-aii/issues

---

## ✅ Success Criteria

Your deployment is **COMPLETE** when:

- ✅ Azure app accessible at `https://{APP_NAME}.azurewebsites.net`
- ✅ Streamlit dashboard loads (8 pages visible)
- ✅ AI Verilog Generator page accessible
- ✅ Can generate Verilog with Groq API
- ✅ Generated files display correctly
- ✅ No 500 errors in logs
- ✅ GitHub Actions shows green checkmarks

---

**Made with ❤️ by Venka**

*Azure Deployment Guide v1.0*
