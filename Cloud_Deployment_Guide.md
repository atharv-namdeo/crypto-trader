# Institutional Cloud Deployment Guide: v11.1.4 "Grandmaster"
Path: Cloud_Deployment_Guide.md

This guide provides the definitive steps to deploy the **v11.1.4 "Grandmaster"** to a Cloud VPS for live **Forward Testing.**

## 1. Prerequisites (Recommended Infrastructure)
- **OS**: Ubuntu 22.04 LTS
- **Specs**: 2 vCPU, 4GB RAM (AWS t3.medium or equivalent)
- **Docker**: Latest Docker Engine + Docker Compose

## 2. Server Preparation
SSH into your VPS and execute the following orchestration commands:

```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# Install Docker Compose
sudo apt install -y docker-compose
```

## 3. Project Deployment
Transfer your project files to the VPS (using SCP or Git) and navigate to the project directory:

```bash
cd crypto-trader

# Build and Launch the Sovereign Architecture
sudo docker-compose up --build -d
```

## 4. Operational Verification
### Live Log Audit
Confirm that the engine is initializing and connecting to Redis:
```bash
sudo docker logs -f grandmaster_engine
```

### Telegram Connectivity
Verify that you have received the **"🤖 QuantBot connected successfully!"** message on your Telegram mobile device. 🛡️⚓🚀

## 5. Security Protocols
> [!WARNING]
> **API Key Safety**: 
> Ensure your `.env` file on the VPS is NOT world-readable. 
> Execute: `chmod 600 .env` 🛡️🧱⚓

---
**Status**: **DEPLOYMENT READY.** Your containerized architecture is now engineered for high-fidelity Cloud operations. 🏺🏛️🏅🚩🏅🏆🚀
