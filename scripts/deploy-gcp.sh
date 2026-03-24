#!/bin/bash
# scripts/deploy-gcp.sh
set -e

PROJECT_ID="crypto-trader-prod"
REGION="us-central1"
SERVICE_NAME="trading-bot"

echo "🚀 Deploying to Google Cloud Run..."

# Build and Push (Simulated)
gcloud builds submit --tag gcr.io/$PROJECT_ID/$SERVICE_NAME:latest

# Deploy
gcloud run deploy $SERVICE_NAME \
  --image gcr.io/$PROJECT_ID/$SERVICE_NAME:latest \
  --platform managed \
  --region $REGION \
  --allow-unauthenticated \
  --memory 4Gi \
  --cpu 2

echo "✅ GCP Deployment Complete!"
