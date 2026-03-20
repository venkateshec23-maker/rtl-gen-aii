# Cloud Deployment Quick Start

**Goal**: Deploy RTL-Gen AI to production using $200 DigitalOcean + $100 AWS credits

---

## 📍 One-Command Deployments

### DigitalOcean (Recommended - 5 minutes)

**Prerequisites**: `doctl` CLI installed and authenticated

```bash
# 1. Create the app (fastest!)
doctl apps create --spec deploy/digitalocean/app.yaml

# That's it! 🎉 Your app is live in ~5 minutes
# Get URL: doctl apps list
```

**Cost**: $27/month ($200 credits = 7+ months deployed)  
**Time to live**: 5 minutes

---

### AWS (Alternative - 20 minutes)

**Prerequisites**: AWS Educate account, `aws` CLI, Docker, ECR access

```bash
# 1. Build and push Docker image
aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin $ACCOUNT_ID.dkr.ecr.us-east-1.amazonaws.com
docker build -t rtl-gen-ai:latest .
docker tag rtl-gen-ai:latest $ACCOUNT_ID.dkr.ecr.us-east-1.amazonaws.com/rtl-gen-ai:latest
docker push $ACCOUNT_ID.dkr.ecr.us-east-1.amazonaws.com/rtl-gen-ai:latest

# 2. Deploy infrastructure
aws cloudformation create-stack \
  --stack-name rtl-gen-ai \
  --template-body file://deploy/aws/cloudformation.yaml \
  --parameters \
    ParameterKey=DBPassword,ParameterValue=YourSecurePassword123 \
    ParameterKey=AnthropicAPIKey,ParameterValue=sk-... \
  --capabilities CAPABILITY_AUTO_EXPAND

# 3. Get the URL
aws elbv2 describe-load-balancers --query 'LoadBalancers[0].DNSName'
```

**Cost**: ~$67/month ($100 credits = 1.5+ months deployed)  
**Time to live**: 20 minutes

---

## 🔴 Deploy Everything (GitHub Actions Automated)

**Prerequisites**: GitHub repository, AWS IAM role, secrets configured

**Just push to main branch!** GitHub Actions will:
1. ✅ Run all tests
2. ✅ Build Docker image
3. ✅ Push to ECR
4. ✅ Update ECS service
5. ✅ Deploy to DigitalOcean (optional)

```bash
git push origin main
# Watch: GitHub Actions tab
```

---

## 📊 Cost Comparison

| Provider | Monthly | 12 months | Credits | Months Covered |
|----------|---------|-----------|---------|-----------------|
| **DigitalOcean** | $27 | $324 | $200 | **7+ months** ✅ |
| **AWS** | $67 | $804 | $100 | **1.5+ months** ⏱️ |
| **Heroku** (PRO) | $50 | $600 | $50 | **1 month** |

---

## 🎯 Recommended Strategy

### Phase 1: Development (Free)
- Local Streamlit: `streamlit run app.py`
- GitHub Student Pack activation
- Set up both environments side-by-side

### Phase 2: Initial Deployment (7+ months)
- **Primary**: Deploy to DigitalOcean immediately
- **Backup**: Prepare AWS for failover
- Monitor cost (should be ~$27/month)

### Phase 3: Growth Phase (Month 8+)
- Switch to AWS Reserved Instances (30% savings)
- Or continue DigitalOcean if costs are acceptable
- Consider multi-region setup

---

## 🔧 Configuration Files

| File | Purpose | Deploy To |
|------|---------|-----------|
| `deploy/digitalocean/app.yaml` | DigitalOcean App Platform spec | DigitalOcean |
| `deploy/digitalocean/database.tf` | Terraform infrastructure | DigitalOcean (Optional) |
| `deploy/aws/cloudformation.yaml` | Complete AWS infrastructure | AWS CloudFormation |
| `deploy/aws/ecs-task.json` | ECS task definition | AWS ECS |
| `Dockerfile` | Container image | Both |
| `.github/workflows/deploy.yml` | CI/CD pipeline | GitHub Actions |
| `python/database.py` | Database ORM | Both |

---

## 🚀 Deployment Checklist

### Before Deployment

- [ ] Clone repository locally
- [ ] Create GitHub account if not exists
- [ ] Apply for GitHub Student Pack: https://education.github.com/pack
- [ ] Activate $200 DigitalOcean credits
- [ ] Activate $100 AWS Educate credits (if using AWS)
- [ ] Have Anthropic/DeepSeek API keys ready

### DigitalOcean Deployment

- [ ] Install `doctl` CLI
- [ ] Authenticate: `doctl auth init`
- [ ] Run: `doctl apps create --spec deploy/digitalocean/app.yaml`
- [ ] Get URL: `doctl apps list`
- [ ] Test app is live

### AWS Deployment (Optional Backup)

- [ ] Set up AWS Educate account
- [ ] Install AWS CLI
- [ ] Install Docker Desktop
- [ ] Create ECR repository
- [ ] Build and push Docker image
- [ ] Deploy CloudFormation stack
- [ ] Get ALB DNS name
- [ ] Test app is live

### GitHub Actions CI/CD

- [ ] Push to GitHub repository
- [ ] Configure secrets in GitHub:
  - `ANTHROPIC_API_KEY`
  - `DEEPSEEK_API_KEY` (optional)
  - `AWS_ACCOUNT_ID` (if using AWS)
  - `DIGITALOCEAN_ACCESS_TOKEN` (if using DigitalOcean)
- [ ] Watch GitHub Actions tab for deployments

---

## 📈 Monitoring

### DigitalOcean

```bash
# View app logs
doctl apps logs <app-id>

# View metrics
doctl monitoring metrics list

# Scale application
doctl apps update <app-id> --spec deploy/digitalocean/app.yaml
```

### AWS

```bash
# View logs
aws logs tail /ecs/rtl-gen-dev --follow

# Check service status
aws ecs describe-services --cluster rtl-gen-cluster-dev --services rtl-gen-service-dev

# View metrics
aws cloudwatch get-metric-statistics --metric-name CPUUtilization --namespace AWS/ECS --start-time 2024-03-20T00:00:00Z --end-time 2024-03-21T00:00:00Z --period 3600 --statistics Average
```

---

## 🐛 Troubleshooting

### App won't start

**DigitalOcean:**
```bash
doctl apps logs <app-id>  # Check error logs
doctl apps get <app-id>    # Check deployment status
```

**AWS:**
```bash
aws logs tail /ecs/rtl-gen-dev --follow
aws ecs describe-tasks --cluster rtl-gen-cluster-dev --tasks <task-id>
```

### Database connection fails

**DigitalOcean:**
- Check database is in "Ready" state
- Verify database name is "rtlgen"
- Check connection string in app.yaml

**AWS:**
- Check RDS security group allows 5432 from ECS
- Verify database endpoint in Secrets Manager
- Check DatabaseURLSecret value

### High costs

**DigitalOcean:**
- Basic size: $12/month
- Database: $15/month
- Total: ~$27/month
- **Upgrade if needed**: Professional+ sizes available

**AWS:**
- ECS: $15/month
- ALB: $16/month
- RDS: $30/month
- Free tier eligibility: 12 months of discounts available

---

## 🎓 Learning Resources

- **DigitalOcean Docs**: https://docs.digitalocean.com/
- **AWS Documentation**: https://docs.aws.amazon.com/
- **GitHub Actions**: https://docs.github.com/en/actions
- **Streamlit Deployment**: https://docs.streamlit.io/knowledge-base/tutorials/deploy

---

## ✅ Success!

Your RTL-Gen AI should now be:
- ✅ Running in production
- ✅ Auto-scaling with traffic
- ✅ Database persisting designs
- ✅ Logs streaming to cloud
- ✅ Automated deployments via GitHub
- ✅ Running for 7+ months on free credits

**Share your deployment URL with the world!** 🌍
