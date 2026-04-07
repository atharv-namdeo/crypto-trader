# Sovereign Optimization: AWS Free Tier Deployment
Path: AWS_Free_Tier_Optimization.md

To run the **v11.1.4 "Grandmaster"** on the AWS Free Tier (`t2.micro` / `t3.micro`) with 1GB RAM, you must execute these institutional optimization protocols.

## 1. Establishing the 2GB Swap Infrastructure
Run these commands on your Ubuntu VPS to prevent "Out of Memory" crashes:

```bash
# Allocate 2GB for the Swap file
sudo fallocate -l 2G /swapfile

# Set permissions
sudo chmod 600 /swapfile

# Format as swap
sudo mkswap /swapfile

# Activate swap
sudo swapon /swapfile

# Ensure persistence across reboots
echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab

# Verify
free -h
```

## 2. Engine Memory Throttling
If you find the CPU usage exceeding 80%, modify your `config.py` temporarily to restrict monitoring to the highest-liquidity assets:

```python
# Optional: Symbol Gating for 1GB RAM
SYMBOLS = SYMBOLS[:15] # Monitor only Top 15 symbols
```

## 3. High-Performance Deployment
Launch the bot using Docker as previously orchestrated:
```bash
sudo docker-compose up --build -d
```

## 4. Why Oracle Cloud Might Be Better
> [!IMPORTANT]
> **Comparison**:
> - **AWS Free Tier**: 1 vCPU, 1GB RAM, **12 Months Only**. 🛡️⚓
> - **Oracle Free Tier**: 4 vCPU, 24GB RAM, **Free Forever**. 🏺🏛️🏅🚩🏅🏆🚀
> 
> If you have the option, the Oracle Ampere A1 (ARM64) instance is the definitive choice for the Grandmaster's ML ensemble monitoring.

---
**Status**: **OPTIMIZATION COMPLETE.** Your engine is now calibrated for AWS Free Tier survival. 🏺🏛️🏅🚩🏅🏆🚀
