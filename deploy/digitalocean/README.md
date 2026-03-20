# Deploy RTL-Gen AI on DigitalOcean

Using **$200 GitHub EDU Credits** to run production RTL-Gen AI for 7+ months!

## Prerequisites

1. **DigitalOcean Account** - Activate your $200 GitHub EDU credits
2. **doctl CLI** - DigitalOcean command-line tool
3. **Terraform** (optional) - For IaC database management
4. **API Keys** - Anthropic, DeepSeek (if using real providers)

## Quick Start (5 minutes)

### 1. Create DigitalOcean Account

- Visit: https://cloud.digitalocean.com
- Sign up with GitHub
- Apply for GitHub Student Program credits
- Balance should show $200

### 2. Install doctl

```bash
# Windows (PowerShell)
> iwr https://github.com/digitalocean/doctl/releases/download/v1.97.0/doctl-1.97.0-windows-amd64.zip -OutFile doctl.zip
> Expand-Archive doctl.zip
> Move-Item doctl.exe "C:\Program Files\doctl.exe"
> $env:PATH += ";C:\Program Files"

# macOS/Linux
$ brew install doctl
```

### 3. Authenticate doctl

```bash
$ doctl auth init
# Enter your API token from DigitalOcean console
# https://cloud.digitalocean.com/account/api/tokens
```

### 4. Deploy to App Platform

```bash
# Set your username
$GITHUB_USER = "yourusername"

# Deploy
$ doctl apps create --spec deploy/digitalocean/app.yaml

# Or deploy directly from spec
$ doctl apps create --spec=./app.yaml --name rtl-gen-ai
```

### 5. Configure Environment Variables

In DigitalOcean App Platform Dashboard:

```
ANTHROPIC_API_KEY = sk-...
DEEPSEEK_API_KEY = sk-...
```

## Database Setup

### Option A: Using App Platform (Simplest)

DigitalOcean App Platform automatically manages PostgreSQL. No additional setup needed!

### Option B: Separate Database (Terraform)

```bash
# 1. Install Terraform
# https://www.terraform.io/downloads

# 2. Set up credentials
export DIGITALOCEAN_TOKEN="your-api-token"

# 3. Deploy database
$ cd deploy/digitalocean
$ terraform init
$ terraform plan
$ terraform apply

# 4. Get connection URL from output
$ terraform output database_url
```

### Option C: Manual Database

```bash
# Create database via web UI
# 1. Dashboard → Databases → Create → PostgreSQL
# 2. Choose size: db-s-1vcpu-1gb
# 3. Keep connection string secure
```

## Cost Breakdown

| Component | Size | Monthly Cost | Annual Cost |
|-----------|------|--------------|------------|
| **App Platform** | professional-xs | $12 | $144 |
| **Database** | db-s-1vcpu-1gb | $15 | $180 |
| **Static Docs** | Free tier | $0 | $0 |
| **Total** | | **$27** | **$324** |

**Your $200 credits covers:**
- 7+ months of production hosting
- Full PostgreSQL database
- Automated backups
- CDN for docs
- Monitoring and logs

## Monitoring & Management

### View Logs

```bash
$ doctl apps logs <app-id> component web
```

### View Metrics

In App Platform Dashboard:
- CPU usage
- Memory usage
- Response times
- Error rates

### Database Backups

DigitalOcean automatically:
- ✅ Creates daily backups
- ✅ Retains 30-day history
- ✅ Enables point-in-time recovery
- ✅ Encrypts backups

### Restore from Backup

```bash
# Via web UI:
# Databases → Select DB → Backups → Restore
# Select date and confirm
```

## Scaling

### When You Hit Limits

**App Platform**:
- Simple: Scale to `professional-m` ($50/month)
- Or add a second instance (load balanced)

**Database**:
- Upgrade to `db-s-2vcpu-4gb` ($30/month)
- Or enable read replicas

```bash
# Scale via CLI
$ doctl apps update <app-id> --instance-size-slug professional-m
```

### Auto-scaling (Future)

DigitalOcean plans to add auto-scaling. For now, monitor usage:

```bash
$ doctl monitoring metrics list <app-id>
```

## Deploying Updates

### Automatic (Recommended)

```yaml
# In app.yaml, enable:
deploy_on_push: true
```

Now every push to `main` auto-deploys within 2 minutes!

### Manual

```bash
$ git push origin main
# The app auto-redeploys via GitHub integration
```

### Check Deployment Status

```bash
$ doctl apps get <app-id>
$ doctl apps list-deployments <app-id>
```

## Cost Management

### Monitor Spending

```bash
# Check current billing
$ doctl billing-history list

# Set up Budget Alert in Settings:
# Dashboard → Account → Billing → Set budget alert at $180/month
```

### Cost Optimization

| Optimization | Saves | Difficulty |
|--------------|-------|-----------|
| Use CDN for static files | $5/mo | Easy |
| Auto-scale down at night | $3/mo | Medium |
| Cache database queries | $2/mo | Hard |
| Use read replicas | Included | Easy |

### Stop Spending (When Needed)

```bash
# Pause app (keeps your code)
$ doctl apps suspend <app-id>

# Resume
$ doctl apps resume <app-id>

# Delete app (if needed)
$ doctl apps delete <app-id>
```

## Troubleshooting

### App won't start

```bash
# Check logs
$ doctl apps logs <app-id> component web

# Common issues:
# - Missing environment variables
# - Port not set to 8080
# - Requirements.txt missing packages
```

### Database connection failed

```bash
# Verify connection URL
$ terraform output database_url

# Check firewall rules allow app
# Databases → Select DB → Connections → Firewall
```

### Out of memory

```bash
# Check app size
$ doctl apps get <app-id>

# Upgrade if needed
$ doctl apps update <app-id> --instance-size-slug professional-m
```

## Advanced Features

### CDN for Static Files

```yaml
# In app.yaml, add:
static_sites:
  - name: assets
    github:
      repo: yourusername/rtl-gen-ai
      branch: main
    source_dir: outputs
    routes:
      - path: /assets
```

### Custom Domain

```bash
# Add domain via web UI or CLI
$ doctl domains create my-rtl-gen.com
$ doctl apps domains add <app-id> my-rtl-gen.com
```

### Monitoring with Datadog

```yaml
# In app.yaml, add:
log_destinations:
  - name: datadog-logs
    datadog:
      api_key: ${DATADOG_API_KEY}
```

## Switching Providers

If you hit $200 limit, switch to AWS:

See: `deploy/aws/README.md`

## Next Steps

1. ✅ Deploy to DigitalOcean
2. ✅ Monitor logs and costs
3. ✅ Set budget alerts
4. ✅ Share with friends (free tier available)
5. ⏳ Prepare AWS backup option

## Support

- DigitalOcean Docs: https://docs.digitalocean.com/
- App Platform: https://docs.digitalocean.com/products/app-platform/
- Community: https://www.digitalocean.com/community

---

**Ready to go live? Your $200 credits await!** 🚀
