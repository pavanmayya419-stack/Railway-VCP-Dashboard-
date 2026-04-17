#!/bin/bash

# Azure Deployment Script
echo "Deploying VCP Dashboard to Azure..."

# Create resource group
az group create --name vcp-rg --location eastus

# Create container registry
az acr create --resource-group vcp-rg --name vcpregistry --sku Basic

# Build and push images
echo "Building Docker images..."
az acr build --registry vcpregistry --image vcp-backend:latest ../backend
az acr build --registry vcpregistry --image vcp-frontend:latest ../frontend

# Create container app environment
az containerapp env create --name vcp-env --resource-group vcp-rg --location eastus

# Deploy backend
az containerapp create \
  --name vcp-backend \
  --resource-group vcp-rg \
  --image vcpregistry.azurecr.io/vcp-backend:latest \
  --environment vcp-env \
  --ingress external \
  --target-port 8000 \
  --env-vars DATABASE_URL=postgresql://... REDIS_URL=redis://...

# Deploy frontend
az containerapp create \
  --name vcp-frontend \
  --resource-group vcp-rg \
  --image vcpregistry.azurecr.io/vcp-frontend:latest \
  --environment vcp-env \
  --ingress external \
  --target-port 80

echo "Deployment complete!"
echo "Frontend URL: $(az containerapp show --name vcp-frontend --resource-group vcp-rg --query properties.configuration.ingress.fqdn -o tsv)"
