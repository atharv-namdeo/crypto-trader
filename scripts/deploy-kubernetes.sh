#!/bin/bash
# scripts/deploy-kubernetes.sh
set -e

NAMESPACE="crypto-trader"
echo "🚀 Deploying Crypto Trader to Kubernetes..."

# Create namespace
kubectl apply -f kubernetes/namespace.yaml

# Apply configs and storage
kubectl apply -f kubernetes/persistent-volumes.yaml

# Apply deployments
kubectl apply -f kubernetes/redis-deployment.yaml
kubectl apply -f kubernetes/prometheus-deployment.yaml
kubectl apply -f kubernetes/grafana-deployment.yaml
kubectl apply -f kubernetes/trading-bot-deployment.yaml

echo "✅ K8s Deployment Complete!"
