# Cloud-Native RTL-Gen AI: Complete Integration Guide

**Status**: ✅ Production-Ready Cloud Platform  
**Credits**: $200 DigitalOcean + $100 AWS  
**Runtime**: 7+ months free deployment  
**Last Updated**: 2024

---

## 📋 Table of Contents

1. Architecture Overview
2. File Structure & Deployment Configs
3. Deployment Paths (DigitalOcean vs AWS)
4. Database Integration
5. CI/CD Pipeline
6. Monitoring & Scaling
7. Cost Optimization
8. Troubleshooting

---

## 🏗️ Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                    Users (Global)                           │
│                                                             │
└────────────────────┬────────────────────────────────────────┘
                     │
        ┌────────────┴────────────┐
        │                         │
   ┌────▼─────┐            ┌─────▼────┐
   │DO CDN     │            │AWS ALB   │
   │(Optional) │            │(HTTP)    │
   └────┬─────┘            └─────┬────┘
        │ HTTPS              │ HTTPS
        │                    │
   ┌────▼─────────────┐  ┌──▼────────────┐
   │DigitalOcean      │  │AWS ECS        │
   │App Platform      │  │Fargate        │
   │Streamlit         │  │Streamlit      │
   └────┬─────────────┘  └──┬────────────┘
        │                    │
   ┌────┴────────────┬───────┴────┐
   │                 │            │
  ┌▼──────────────┐ ┌▼──────────┐ ┌▼──────────┐
  │PostgreSQL     │ │PostgreSQL │ │S3 Storage │
  │(DO Database)  │ │(AWS RDS)  │ │(Optional) │
  └┬──────────────┘ └┬──────────┘ └───────────┘
   │                │
   └────┬───────────┘
        │
   ┌────▼─────────────┐
   │SQLAlchemy ORM    │
   │(python/database.py)
   └──────────────────┘
```

### Technology Stack

**Frontend & Runtime**
- Streamlit 1.31.0 (Web UI)
- Python 3.11+ runtime
- Docker containerization

**Data Layer**
- PostgreSQL 15 (Managed)
- SQLAlchemy 2.0+ (ORM)
- Design persistence (14 fields)

**Cloud Platforms**
- DigitalOcean App Platform (Primary)
- AWS ECS Fargate + ALB (Secondary)
- AWS RDS (Database backup option)

**DevOps**
- GitHub Actions (CI/CD)
- Docker Registry (ECR)
- Terraform (IaC - Optional)
- CloudWatch (Monitoring)

---

## 📁 File Structure & Deployment Configs

### Core Application Files (Unchanged)

```
app.py                              # Main Streamlit application
python/
├── llm_client.py                   # Multi-LLM support (Claude, DeepSeek)
├── waveform_generator.py           # Waveform generation + visualization
├── synthesis_engine.py             # RTL synthesis
├── testbench_generator.py          # Testbench generation
└── database.py                     # ✨ NEW: Database ORM layer
```

### Cloud Deployment Files (NEW)

```
deploy/
├── digitalocean/
│   ├── app.yaml                    # DO App Platform spec
│   ├── database.tf                 # Terraform config (optional)
│   └── README.md                   # DigitalOcean guide (250+ lines)
│
└── aws/
    ├── cloudformation.yaml         # Complete AWS infrastructure
    ├── ecs-task.json               # ECS task definition
    └── README.md                   # AWS deployment guide

.github/workflows/
└── deploy.yml                      # GitHub Actions CI/CD pipeline

Dockerfile                          # ✨ UPDATED: Multi-stage, production-ready
CLOUD_DEPLOYMENT_QUICKSTART.md      # Quick reference guide
```

---

## 🚀 Deployment Paths

### Path 1: DigitalOcean (⭐ RECOMMENDED)

**Why**: Simplest, cost-effective, 7+ months free  
**Time**: 5 minutes  
**Cost**: $27/month ($200 credits = 7+ months)

```bash
# Step 1: Install doctl
# Windows:
winget install DigitalOcean.Doctl

# Step 2: Authenticate
doctl auth init

# Step 3: Deploy!
doctl apps create --spec deploy/digitalocean/app.yaml

# Step 4: Get your URL
doctl apps list
# Output: https://rtl-gen-ai-xxxx.ondigitalocean.app
```

**What's Included**:
- ✅ Streamlit web service ($12/month)
- ✅ PostgreSQL 15 database ($15/month)
- ✅ Automatic HTTPS/SSL
- ✅ Auto-scaling (within tier)
- ✅ Auto-deploy on GitHub push
- ✅ Built-in CI/CD

**Infrastructure Code**: `deploy/digitalocean/app.yaml`
- 89 lines of YAML
- Defines: App service, PostgreSQL DB, environment variables, secrets
- Deploy command: `doctl apps create --spec deploy/digitalocean/app.yaml`

---

### Path 2: AWS (🔄 BACKUP OPTION)

**Why**: Enterprise-grade, scalable, $100 credits available  
**Time**: 20 minutes  
**Cost**: ~$67/month ($100 credits = 1.5+ months)

```bash
# Step 1: Build Docker image
docker build -t rtl-gen-ai:latest .

# Step 2: Push to ECR
aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin $ACCOUNT_ID.dkr.ecr.us-east-1.amazonaws.com
docker tag rtl-gen-ai:latest $ACCOUNT_ID.dkr.ecr.us-east-1.amazonaws.com/rtl-gen-ai:latest
docker push $ACCOUNT_ID.dkr.ecr.us-east-1.amazonaws.com/rtl-gen-ai:latest

# Step 3: Deploy CloudFormation stack
aws cloudformation create-stack \
  --stack-name rtl-gen-ai \
  --template-body file://deploy/aws/cloudformation.yaml \
  --parameters \
    ParameterKey=Environment,ParameterValue=prod \
    ParameterKey=DBPassword,ParameterValue=YourSecurePassword123 \
    ParameterKey=AnthropicAPIKey,ParameterValue=sk-... \
  --capabilities CAPABILITY_AUTO_EXPAND

# Step 4: Get URL
aws elbv2 describe-load-balancers --query 'LoadBalancers[0].DNSName'
# Output: rtl-gen-alb-prod-xxx.us-east-1.elb.amazonaws.com
```

**What's Included**:
- ✅ VPC with public/private subnets
- ✅ Application Load Balancer (HTTP/HTTPS)
- ✅ ECS Fargate (serverless containers)
- ✅ RDS Aurora PostgreSQL
- ✅ Auto-scaling (1-3 instances)
- ✅ CloudWatch monitoring
- ✅ Secrets Manager integration
- ✅ IAM roles and policies

**Infrastructure Code**: `deploy/aws/cloudformation.yaml`
- 600+ lines of CloudFormation YAML
- Defines: VPC, ALB, ECS, RDS, IAM, Auto-scaling, Monitoring
- Deploy command: `aws cloudformation create-stack ...`

---

## 💾 Database Integration

### New: python/database.py

**Purpose**: Persistent design storage with multi-provider support

**Features**:
```python
class DesignDatabase:
    # CRUD Operations
    save_design(prompt, rtl_code, testbench, ...)     # Save design
    get_design(design_id)                              # Fetch design
    search_designs(query, tags, provider)              # Search
    list_public_designs()                              # Browse public
    update_design(design_id, **kwargs)                 # Modify
    delete_design(design_id)                           # Remove
    
    # Analytics
    get_stats()                                         # Usage stats

# Streamlit Integration
add_database_integration(db)                           # Add DB UI
add_analytics_view(db)                                 # Show stats
```

**Design Model** (14 fields):
```python
{
    id: str,                    # UUID
    prompt: str,                # User prompt
    rtl_code: str,              # Generated RTL
    testbench_code: str,        # Testbench code
    waveform_path: str,         # Waveform VCD file
    synthesis_path: str,        # Synthesis result
    provider: str,              # "claude" / "deepseek"
    model: str,                 # Model name
    metadata: dict,             # Custom JSON
    tags: list,                 # ["uart", "verilog"]
    is_public: bool,            # Share with others
    created_at: datetime,
    updated_at: datetime,
    created_by: str             # Username
}
```

**Database Support**:
- ✅ PostgreSQL (production)
- ✅ SQLite (development)
- ✅ Graceful degradation (works without DB)

**Connections**:
- **DigitalOcean**: Automatically configured in `app.yaml`
- **AWS**: Set via `DATABASE_URL` secret in Secrets Manager

---

## 🔄 CI/CD Pipeline

### GitHub Actions: `.github/workflows/deploy.yml`

**Triggers**:
- On push to `main` branch
- On pull requests

**Workflow**:

```
1. Test Phase
   ├─ Python 3.11 tests
   ├─ Python 3.12 tests
   ├─ Lint (flake8)
   ├─ Code coverage
   └─ Upload to Codecov

2. Build Phase (on main push only)
   ├─ Build Docker image
   ├─ Push to ECR
   ├─ Update ECS service (auto-deploy)
   └─ Deploy to DigitalOcean (optional)

3. Notification Phase
   └─ Report status
```

**Configuration**:

Create GitHub Secrets:
```
ANTHROPIC_API_KEY    # LLM provider key
DEEPSEEK_API_KEY     # Alternative LLM key
AWS_ACCOUNT_ID       # For ECR push
DIGITALOCEAN_ACCESS_TOKEN  # For DO apps update
```

**Usage**:
```bash
git push origin main
# Watch progress at: GitHub → Actions tab
# Auto-deploys to both DigitalOcean and AWS
```

---

## 📊 Monitoring & Scaling

### DigitalOcean Monitoring

```bash
# View logs (real-time)
doctl apps logs <app-id> --follow

# Check app status
doctl apps get <app-id>

# View metrics
doctl monitoring metrics list

# Manual scaling (change spec)
doctl apps update <app-id> --spec deploy/digitalocean/app.yaml
```

### AWS Monitoring

```bash
# View ECS logs
aws logs tail /ecs/rtl-gen-prod --follow

# Check service metrics
aws cloudwatch get-metric-statistics \
  --metric-name CPUUtilization \
  --namespace AWS/ECS \
  --start-time ... --end-time ... --period 3600 \
  --statistics Average

# View alarms
aws cloudwatch describe-alarms --alarm-names rtl-gen-high-cpu-prod

# Check auto-scaling status
aws application-autoscaling describe-scaling-activities \
  --service-namespace ecs
```

### Built-in Alerts

**DigitalOcean**:
- Email alerts on deployment failure
- Automatic rollback on service restart failure

**AWS CloudWatch**:
- High CPU (>80%)
- High Memory (>80%)
- ALB unhealthy targets

---

## 💰 Cost Optimization

### Budget Breakdown

| Component | DO | AWS | Total |
|-----------|----|----|--------|
| Compute | $12 | $15 | $27 |
| Database | $15 | $30 | $45 |
| Load Balancer | - | $16 | $16 |
| Monitoring | - | $5 | $5 |
| Data Transfer | - | $1 | $1 |
| **Monthly** | **$27** | **$67** | **$94** |
| **Credits** | **$200** | **$100** | **$300** |
| **Runway** | **7+ months** | **1.5 months** | **N/A** |

### Optimizations

**Phase 1: Free Tier (Months 1-12)**
- Use AWS free tier where possible
- DO app platform is generally cheaper

**Phase 2: Cost Reduction (After free trial)**
- Reserved instances: 30% savings
- Spot instances: 70% savings
- Smaller instance types
- Auto-scaling policies

**Phase 3: Multi-Region (Optional)**
- DigitalOcean: $27/month per region
- AWS: $67/month per region
- Consider failover vs cost

---

## 🐛 Troubleshooting

### Deployment Issues

**DigitalOcean App won't start**:
```bash
doctl apps logs <app-id>              # Check error
doctl apps get <app-id>               # Check status
```

**AWS CloudFormation stack failed**:
```bash
aws cloudformation describe-stack-events --stack-name rtl-gen-ai
aws cloudformation describe-stacks --stack-name rtl-gen-ai --query 'Stacks[0].StackStatus'
```

### Database Connection Issues

**Check database is ready**:
```bash
# DigitalOcean
doctl databases list

# AWS
aws rds describe-db-instances --db-instance-identifier rtl-gen-db-prod
```

**Test connection locally**:
```bash
psql postgresql://user:pass@host:5432/rtlgen
# Or use python-dotenv + sqlalchemy
```

### Performance Issues

**Check metrics**:
```bash
# DigitalOcean: doctl monitoring
# AWS: CloudWatch console

# Common causes:
# 1. Database connection pooling (add in app.yaml)
# 2. Memory too small (increase TaskMemory in CloudFormation)
# 3. Too many concurrent users (scale to 2-3 instances)
```

---

## ✅ Deployment Checklist

### Pre-Deployment

- [ ] GitHub repository created and pushed
- [ ] GitHub Student Pack activated
- [ ] DigitalOcean credits ($200) activated
- [ ] AWS Educate account setup ($100)
- [ ] Anthropic API key obtained (sk-...)
- [ ] DeepSeek API key obtained (optional)
- [ ] All local tests passing (`pytest tests/`)

### DigitalOcean Deployment

- [ ] `doctl` CLI installed
- [ ] Authenticated: `doctl auth init`
- [ ] Deploy: `doctl apps create --spec deploy/digitalocean/app.yaml`
- [ ] Verify: Check URL is accessible
- [ ] Test: Run through UI workflow

### AWS Deployment (Optional)

- [ ] AWS CLI configured
- [ ] Docker installed and running
- [ ] ECR repository created
- [ ] Image built and pushed to ECR
- [ ] CloudFormation stack deployed
- [ ] Database initialized
- [ ] Secrets created in Secrets Manager
- [ ] Service reaching desired count

### GitHub Actions Setup

- [ ] Push code to GitHub
- [ ] Configure GitHub Secrets:
  - [ ] `ANTHROPIC_API_KEY`
  - [ ] `AWS_ACCOUNT_ID` (if using AWS)
  - [ ] `DIGITALOCEAN_ACCESS_TOKEN` (if using DO)
- [ ] Watch first deployment in Actions tab
- [ ] Verify auto-deployment on next push

---

## 🎯 Next Steps

### Immediate (This Week)
1. ✅ Deploy to DigitalOcean (5 minutes)
2. ✅ Test all features in production
3. ✅ Set up GitHub repository with Actions

### Short-term (This Month)
1. Monitor costs and performance
2. Collect user feedback
3. Iterate on UI/features
4. Set up custom domain (if desired)

### Medium-term (Month 3+)
1. Evaluate AWS as backup
2. Consider multi-region setup
3. Implement advanced monitoring
4. Set up automated backups

---

## 📚 Documentation References

- **DigitalOcean Docs**: https://docs.digitalocean.com/
- **AWS Documentation**: https://docs.aws.amazon.com/
- **Streamlit Deployment**: https://docs.streamlit.io/knowledge-base/tutorials/deploy
- **GitHub Actions**: https://docs.github.com/en/actions
- **PostgreSQL**: https://www.postgresql.org/docs/

---

## 🎉 You're Ready!

Your RTL-Gen AI is now ready for production deployment:

✅ Code is containerized (Dockerfile)  
✅ Database layer is implemented (python/database.py)  
✅ Infrastructure is defined (CloudFormation + app.yaml)  
✅ CI/CD is automated (GitHub Actions)  
✅ Monitoring is configured (CloudWatch + DO metrics)  
✅ Deployment is simple (one command!)

**Time to deploy: 5 minutes on DigitalOcean**

Choose your path:
- **DigitalOcean** (recommended): `doctl apps create --spec deploy/digitalocean/app.yaml`
- **AWS**: `aws cloudformation create-stack --stack-name rtl-gen-ai --template-body file://deploy/aws/cloudformation.yaml ...`
- **GitHub Actions** (automated): `git push origin main`

---

**Questions?** Check the deployment-specific guides:
- DigitalOcean: `deploy/digitalocean/README.md`
- AWS: `deploy/aws/README.md`
- Quick Start: `CLOUD_DEPLOYMENT_QUICKSTART.md`

🚀 **Let's deploy!**
