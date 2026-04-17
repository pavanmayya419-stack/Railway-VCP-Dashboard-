# Cloud Deployment Guide

## Quick Deployment Options

### 1. AWS (Recommended for Production)
```bash
cd deploy/aws
chmod +x deploy.sh
./deploy.sh
```

**Requirements:**
- AWS CLI installed
- ECR repository created
- ECS cluster configured

**Cost:** ~$50-100/month for t3.medium + RDS

### 2. Azure (Easiest with Container Apps)
```bash
cd deploy/azure
chmod +x deploy.sh
./deploy.sh
```

**Requirements:**
- Azure CLI installed
- Azure subscription

**Cost:** ~$40-80/month with free tier

### 3. GCP (Best for Serverless)
```bash
cd deploy/gcp
chmod +x deploy.sh
./deploy.sh
```

**Requirements:**
- gcloud CLI installed
- GCP project with billing enabled

**Cost:** ~$30-70/month with Cloud Run

### 4. Railway (Simplest)
```bash
# Install Railway CLI
npm install -g @railway/cli

# Login
railway login

# Deploy
railway up
```

**Cost:** ~$20-50/month
- No configuration needed
- Automatic GitHub integration
- Built-in PostgreSQL

### 5. Render (Alternative to Railway)
```bash
# Connect GitHub repo to render.com
# Auto-deploys on push
```

**Cost:** ~$25-60/month
- Free SSL certificates
- Postgres included
- Easy setup

## Database Setup

For production, you'll need:
1. **PostgreSQL** for scan results
2. **Redis** for caching
3. **S3/Cloud Storage** for OHLCV data

## Environment Variables

Set these in your cloud provider:
```bash
DATABASE_URL=postgresql://user:pass@host:5432/db
REDIS_URL=redis://host:6379
API_KEY=your_secret_key
ENVIRONMENT=production
```

## Monitoring

Add monitoring with:
- **Sentry** for error tracking
- **LogRocket** for session replay
- **Prometheus/Grafana** for metrics

## Automation

Set up GitHub Actions for CI/CD:
```yaml
# .github/workflows/deploy.yml
name: Deploy
on:
  push:
    branches: [main]
jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Deploy to Cloud
        run: ./deploy/deploy.sh
```

## Keeping It Running 24/7

1. **Use managed services** (RDS, Cloud SQL, etc.)
2. **Set up health checks**
3. **Configure auto-scaling**
4. **Add backup schedules**
5. **Monitor with alerts**
