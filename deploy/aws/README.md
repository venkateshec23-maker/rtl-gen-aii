# Deploy RTL-Gen AI on AWS

Using **$100 AWS Educate Credits** as backup/secondary deployment!

## Prerequisites

1. **AWS Educate Account** - Apply for GitHub Student Program
2. **AWS CLI** - Command-line interface
3. **Docker** - For building container images
4. **Account ID** - Your 12-digit AWS account ID

## Cost Breakdown (Budget: $100/month)

| Service | Size | Monthly Cost | Notes |
|---------|------|--------------|-------|
| ECS Fargate | 0.5 CPU, 1GB RAM | $15 | Pay per second |
| Application Load Balancer | Standard | $16 | ~$0.006/hour |
| RDS Aurora PostgreSQL | db.t3.small | $30 | Serverless option available |
| Data Transfer | 10GB | $1 | Usually minimal |
| CloudWatch Logs | <100GB | $5 | Auto-retention |
| **Total** | | **$67/month** | **stays within $100 budget** |

## Quick Start (30 minutes)

### 1. Setup AWS Educate

- Get started at: https://www.awseducate.com/
- Create account with GitHub
- Accept terms
- Activate $100 credits

### 2. Install AWS CLI

```powershell
# Windows using winget
> winget install Amazon.AWSCLI

# Or direct download
> Invoke-WebRequest -Uri "https://awscli.amazonaws.com/AWSCLIV2.msi" -OutFile AWSCLIV2.msi
> msiexec.exe /i AWSCLIV2.msi

# Verify
> aws --version
```

### 3. Configure AWS Credentials

```powershell
> aws configure
AWS Access Key ID: AKIAIOSFODNN7EXAMPLE
AWS Secret Access Key: wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY
Default region name: us-east-1
Default output format: json
```

### 4. Create ECR Repository

```bash
# Create repository for Docker images
$ aws ecr create-repository --repository-name rtl-gen-ai --region us-east-1

# Output: Get the repository URL
# Example: 123456789012.dkr.ecr.us-east-1.amazonaws.com/rtl-gen-ai
```

### 5. Create Docker Image

```bash
# Create Dockerfile in project root
# (See Dockerfile section below)

# Build image
$ docker build -t rtl-gen-ai:latest .

# Tag for ECR
$ docker tag rtl-gen-ai:latest 123456789012.dkr.ecr.us-east-1.amazonaws.com/rtl-gen-ai:latest

# Login to ECR
$ aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin 123456789012.dkr.ecr.us-east-1.amazonaws.com

# Push image
$ docker push 123456789012.dkr.ecr.us-east-1.amazonaws.com/rtl-gen-ai:latest
```

### 6. Create RDS Database

```bash
# Create PostgreSQL database
$ aws rds create-db-instance \
    --db-instance-identifier rtl-gen-db \
    --db-instance-class db.t3.micro \
    --engine postgres \
    --engine-version 15.3 \
    --master-username rtl_admin \
    --master-user-password MySecurePassword123 \
    --allocated-storage 20 \
    --storage-type gp2 \
    --publicly-accessible true \
    --region us-east-1

# Wait for database to be ready (5-10 minutes)
$ aws rds describe-db-instances --db-instance-identifier rtl-gen-db --query 'DBInstances[0].DBInstanceStatus'
```

### 7. Store Secrets in AWS Secrets Manager

```bash
# Store API keys
$ aws secretsmanager create-secret \
    --name anthropic-key \
    --secret-string '{"ANTHROPIC_API_KEY":"sk-..."}'

$ aws secretsmanager create-secret \
    --name deepseek-key \
    --secret-string '{"DEEPSEEK_API_KEY":"sk-..."}'

$ aws secretsmanager create-secret \
    --name database-url \
    --secret-string 'postgresql://rtl_admin:password@rtl-gen-db.c9akciq32.us-east-1.rds.amazonaws.com:5432/rtlgen'
```

### 8. Create ECS Cluster and Service

```bash
# Create cluster
$ aws ecs create-cluster --cluster-name rtl-gen-cluster

# Register task definition
$ aws ecs register-task-definition --cli-input-json file://deploy/aws/ecs-task.json

# Create service (requires ALB setup first - see below)
$ aws ecs create-service \
    --cluster rtl-gen-cluster \
    --service-name rtl-gen-service \
    --task-definition rtl-gen-ai:1 \
    --desired-count 1 \
    --launch-type FARGATE \
    --load-balancers targetGroupArn=arn:aws:elasticloadbalancing:us-east-1:123456789012:targetgroup/rtl-gen-tg/1234567890123456,containerName=rtl-gen-ai,containerPort=8501
```

## Dockerfile

Create `Dockerfile` in project root:

```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    git \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY . .

# Expose port
EXPOSE 8501

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:8501/_stcore/health || exit 1

# Run Streamlit
CMD ["streamlit", "run", "app.py", "--server.port=8501", "--server.headless=true"]
```

## Monitoring & Logging

### View Logs

```bash
# Get log group name
$ aws logs describe-log-groups

# View logs
$ aws logs tail /ecs/rtl-gen-ai --follow

# Get specific time range
$ aws logs get-log-events \
    --log-group-name /ecs/rtl-gen-ai \
    --log-stream-name ecs/rtl-gen-ai/unique-id \
    --start-time $(date -d '30 minutes ago' +%s)000
```

### CloudWatch Dashboard

```bash
# Create dashboard
$ aws cloudwatch put-dashboard \
    --dashboard-name RTL-Gen-AI \
    --dashboard-body '{
        "widgets": [
            {
                "type": "metric",
                "properties": {
                    "metrics": [
                        ["AWS/ECS", "CPUUtilization", {"stat": "Average"}],
                        ["AWS/ECS", "MemoryUtilization", {"stat": "Average"}]
                    ],
                    "period": 300,
                    "stat": "Average",
                    "region": "us-east-1"
                }
            }
        ]
    }'
```

### Set Up Alarms

```bash
# CPU too high
$ aws cloudwatch put-metric-alarm \
    --alarm-name rtl-gen-high-cpu \
    --alarm-description "Alert when CPU > 80%" \
    --metric-name CPUUtilization \
    --namespace AWS/ECS \
    --statistic Average \
    --period 300 \
    --threshold 80 \
    --comparison-operator GreaterThanThreshold \
    --evaluation-periods 2
```

## Scaling

### Auto-scaling

```bash
# Create auto-scaling target (scale 1-3 instances)
$ aws application-autoscaling register-scalable-target \
    --service-namespace ecs \
    --resource-id service/rtl-gen-cluster/rtl-gen-service \
    --scalable-dimension ecs:service:DesiredCount \
    --min-capacity 1 \
    --max-capacity 3

# Scale policy: target CPU 70%
$ aws application-autoscaling put-scaling-policy \
    --policy-name rtl-gen-cpu-scaling \
    --service-namespace ecs \
    --resource-id service/rtl-gen-cluster/rtl-gen-service \
    --scalable-dimension ecs:service:DesiredCount \
    --policy-type TargetTrackingScaling \
    --target-tracking-scaling-policy-configuration '{
        "TargetValue": 70,
        "PredefinedMetricSpecification": {
            "PredefinedMetricType": "ECSServiceAverageCPUUtilization"
        },
        "ScaleOutCooldown": 60,
        "ScaleInCooldown": 300
    }'
```

### Manual Scaling

```bash
# Scale to 3 instances
$ aws ecs update-service \
    --cluster rtl-gen-cluster \
    --service rtl-gen-service \
    --desired-count 3
```

## Cost Optimization

### Reserved Instances

Save 30-40% with yearly commitment:

```bash
# Describe on-demand pricing
$ aws ec2 describe-spot-price-history --instance-types t3.small
```

### Spot Instances

Use Spot for non-critical tasks (70% savings):

```bash
# Update ECS service to use SPOT
# (Requires modifying task definition with capacity provider strategy)
```

### Free Tier Eligible

For first 12 months:
- ✅ 750 hours ECS Fargate (0.25-0.5 CPU)
- ✅ 750 hours RDS db.t2.micro (slightly older, but still available)
- ✅ 20GB EBS
- ✅ 1GB data transfer

## Adding Load Balancer

```bash
# Create security group for ALB
$ aws ec2 create-security-group \
    --group-name rtl-gen-alb-sg \
    --description "Security group for RTL-Gen ALB"

# Create ALB
$ aws elbv2 create-load-balancer \
    --name rtl-gen-alb \
    --subnets subnet-123456 subnet-789012 \
    --security-groups sg-0123456

# Create target group
$ aws elbv2 create-target-group \
    --name rtl-gen-tg \
    --protocol HTTP \
    --port 8501 \
    --vpc-ide vpc-12345

# Create listener
$ aws elbv2 create-listener \
    --load-balancer-arn arn:aws:elasticloadbalancing:... \
    --protocol HTTP \
    --port 80 \
    --default-actions Type=forward,TargetGroupArn=arn:aws:elasticloadbalancing:...
```

## Troubleshooting

### Task won't start

```bash
# Check task details
$ aws ecs describe-tasks \
    --cluster rtl-gen-cluster \
    --tasks <task-id>

# Check logs
$ aws logs tail /ecs/rtl-gen-ai
```

### Database connection fails

```bash
# Verify security group allows connections
$ aws ec2 describe-security-groups --group-ids sg-12345

# Check RDS endpoint
$ aws rds describe-db-instances --db-instance-identifier rtl-gen-db
```

### Costs higher than expected

```bash
# Check costs
$ aws ce get-cost-and-usage \
    --time-period Start=2024-03-01,End=2024-03-31 \
    --granularity MONTHLY \
    --metrics "BlendedCost"
```

## Backup & Restore

### RDS Backups

```bash
# Create manual snapshot
$ aws rds create-db-snapshot \
    --db-instance-identifier rtl-gen-db \
    --db-snapshot-identifier rtl-gen-backup-$(date +%Y%m%d)

# List snapshots
$ aws rds describe-db-snapshots

# Restore from snapshot
$ aws rds restore-db-instance-from-db-snapshot \
    --db-instance-identifier rtl-gen-db-restored \
    --db-snapshot-identifier rtl-gen-backup-20240320
```

## Next Steps

1. ✅ Test deployment on AWS ($100 credits)
2. ✅ Monitor costs and scalability
3. ✅ Set up auto-scaling
4. ✅ Add monitoring/alerts
5. ⏳ Switch to DigitalOcean if costs exceed $50/month

## Support

- AWS Documentation: https://docs.aws.amazon.com/
- ECS: https://docs.aws.amazon.com/ecs/
- Educate: https://www.awseducate.com/

---

**Your $100 AWS credits are ready to deploy!** 🚀
