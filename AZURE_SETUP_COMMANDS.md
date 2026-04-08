# Azure Setup Commands — Copy & Paste Ready

## Step 1: Login (DO THIS IN VS CODE TERMINAL)
```powershell
az login
```
Wait for browser to open and sign in with your Azure account.

## Step 2: Create Resource Group
```powershell
az group create --name rtl-gen-ai --location eastus
```

## Step 3: Create App Service Plan (Free Tier)
```powershell
az appservice plan create `
  --name rtl-gen-plan `
  --resource-group rtl-gen-ai `
  --sku FREE `
  --is-linux
```

## Step 4: Create Web App
```powershell
$APP_NAME = "rtl-gen-ai-venka"

az webapp create `
  --resource-group rtl-gen-ai `
  --plan rtl-gen-plan `
  --name $APP_NAME `
  --runtime "PYTHON|3.11"

# Save this value
Write-Host "Your app name: $APP_NAME" -ForegroundColor Green
```

## Step 5: Get Publish Profile
```powershell
$APP_NAME = "rtl-gen-ai-venka"

az webapp deployment profile show `
  --resource-group rtl-gen-ai `
  --name $APP_NAME | Out-File publishProfile.json

# Display it
Get-Content publishProfile.json
```

## Step 6: Copy Publish Profile to Clipboard
```powershell
Get-Content publishProfile.json -Raw | Set-Clipboard
Write-Host "Publish profile copied to clipboard!" -ForegroundColor Green
```

## Step 7: Add GitHub Secrets
Go to: https://github.com/venkateshec23-maker/rtl-gen-aii/settings/secrets/actions

Create 3 secrets with these names:
1. `AZURE_APP_NAME` = rtl-gen-ai-venka
2. `AZURE_PUBLISH_PROFILE` = (paste from clipboard)
3. `GROQ_API_KEY` = gsk_XXXXX... (your API key)

## Step 8: Deploy to Azure
```powershell
cd C:\Users\venka\Documents\rtl-gen-aii

git add .
git commit -m "Deploy to Azure"
git push origin main
```

GitHub Actions will automatically deploy!

## Step 9: Check Deployment
Go to: https://github.com/venkateshec23-maker/rtl-gen-aii/actions

Wait for workflow to complete (2-3 minutes)

## Step 10: Access Your App
```
https://rtl-gen-ai-venka.azurewebsites.net
```

---

**You are here: STEP 1 - Login**
When ready, run `az login` in VS Code terminal and let me know when it's done
