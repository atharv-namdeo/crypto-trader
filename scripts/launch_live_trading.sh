#!/bin/bash
# scripts/launch_live_trading.sh

set -e

echo "🚀 CRYPTO TRADER - LIVE TRADING LAUNCH"
echo "========================================"

# Step 1: Validation
echo "Step 1/5: Running pre-launch validation..."
python -c "import asyncio; from execution.pre_launch_validator import PreLaunchValidator; from core.state_manager import StateManager; s=StateManager(); asyncio.run(s.connect()); v=PreLaunchValidator(s); success=asyncio.run(v.run_full_validation()); v.print_validation_report(); exit(0 if success else 1)"

if [ $? -ne 0 ]; then
    echo "❌ Validation failed. Fixing issues and restarting..."
    exit 1
fi

# Step 2: Database backup (if redis-cli available)
echo "Step 2/5: Backing up Redis state..."
if command -v redis-cli &> /dev/null
then
    redis-cli --rdb /backups/redis-$(date +%s).rdb || echo "⚠️ Redis backup failed, but continuing..."
else
    echo "⚠️ redis-cli not found, skipping backup."
fi

# Step 3: Start monitoring
echo "Step 4/5: Enabling live trading mode..."
export ENABLE_LIVE_TRADING=true
export PAPER_TRADING=false

# Step 5: Start bot
echo "Step 5/5: Starting bot with graduated rollout..."
python main.py

# Cleanup on exit
trap "echo '🛑 Shutting down...'" EXIT
