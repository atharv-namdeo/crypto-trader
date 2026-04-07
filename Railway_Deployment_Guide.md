# Institutional Deployment Guide: Railway Cloud Orchestration
Path: Railway_Deployment_Guide.md

This guide provides the definitive steps to deploy the **v11.1.4 "Grandmaster"** to Railway for high-fidelity **Forward Testing.**

## 1. Project Initialization
- Ensure your project is pushed to a **GitHub repository.**
- Log in to [Railway.app](https://railway.app) and connect your GitHub account.

## 2. Service Orchestration
1.  **New Project**: Click "Empty Project."
2.  **Add Redis**: Press `Cmd+K` (or `Ctrl+K`) and type "Redis." Add a managed Redis service. 🏺🏛️🏅
3.  **Add Trading Engine**: Click "New Service" -> "GitHub Repo" -> Select `crypto-trader`.

## 3. Environment Variable Configuration
Navigate to the "Variables" tab of your `crypto-trader` service and add the following from your `.env` file:

- `BINANCE_DEMO_API_KEY`: [Your Key]
- `BINANCE_DEMO_API_SECRET`: [Your Secret]
- `TELEGRAM_BOT_TOKEN`: [Your Token]
- `TELEGRAM_CHAT_ID`: [Your Chat ID]
- `DRY_RUN`: `true` 🛡️⚓
- `BINANCE_TESTNET`: `true` 🏜️⛵
- `PYTHONPATH`: `.`
- `PORT`: `8000`

> [!TIP]
> **Redis Connection**:
> You do NOT need to manually set the Redis host. Railway will automatically inject the `REDIS_URL` if you have added the Redis service to the project. 🏹🛰️

## 4. Verification
Once the deployment build finishes:
1.  **Check Logs**: Ensure the **Sovereign Shield Activation** log appears.
2.  **Mobile Alert**: Confirm receipt of the **"🚀 QUANT ENGINE STARTED"** notification on Telegram. 🏹🛰️

---
**Status**: **RAILWAY READY.** Your cloud architecture is now engineered for 1-click execution. 🏺🏛️🏅🚩🏅🏆🚀
