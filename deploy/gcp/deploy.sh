#!/bin/bash

# GCP Deployment Script
echo "Deploying VCP Dashboard to GCP..."

# Set project
gcloud config set project YOUR_PROJECT_ID

# Enable APIs
gcloud services enable run.googleapis.com
gcloud services enable sql-component.googleapis.com
gcloud services enable redis.googleapis.com

# Build and push images
echo "Building Docker images..."
gcloud builds submit --tag gcr.io/YOUR_PROJECT_ID/vcp-backend ../backend
gcloud builds submit --tag gcr.io/YOUR_PROJECT_ID/vcp-frontend ../frontend

# Deploy to Cloud Run
echo "Deploying to Cloud Run..."

# Backend
gcloud run deploy vcp-backend \
  --image gcr.io/YOUR_PROJECT_ID/vcp-backend \
  --platform managed \
  --region us-central1 \
  --allow-unauthenticated \
  --set-env-vars DATABASE_URL=postgresql://...,REDIS_URL=redis://...

# Frontend
gcloud run deploy vcp-frontend \
  --image gcr.io/YOUR_PROJECT_ID/vcp-frontend \
  --platform managed \
  --region us-central1 \
  --allow-unauthenticated

echo "Deployment complete!"
echo "Backend URL: $(gcloud run services describe vcp-backend --region us-central1 --format='value(status.url)')"
echo "Frontend URL: $(gcloud run services describe vcp-frontend --region us-central1 --format='value(status.url)')"
