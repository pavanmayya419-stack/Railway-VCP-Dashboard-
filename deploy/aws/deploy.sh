#!/bin/bash

# AWS Deployment Script
echo "Deploying VCP Dashboard to AWS..."

# Build and push images
echo "Building Docker images..."
docker-compose -f docker-compose.yml build

# Tag for ECR (replace with your ECR repo)
aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin YOUR_ECR_REPO.dkr.ecr.us-east-1.amazonaws.com

docker tag vcp-dashboard_backend:latest YOUR_ECR_REPO.dkr.ecr.us-east-1.amazonaws.com/vcp-backend:latest
docker tag vcp-dashboard_frontend:latest YOUR_ECR_REPO.dkr.ecr.us-east-1.amazonaws.com/vcp-frontend:latest

docker push YOUR_ECR_REPO.dkr.ecr.us-east-1.amazonaws.com/vcp-backend:latest
docker push YOUR_ECR_REPO.dkr.ecr.us-east-1.amazonaws.com/vcp-frontend:latest

# Deploy to ECS (or use AWS Copilot)
echo "Deploying to ECS..."
aws ecs update-service --cluster vcp-cluster --service vcp-service --force-new-deployment

echo "Deployment complete!"
