"""
core/multi_strategy_manager.py
Multi-Strategy Orchestrator — Phase 22
Registers multiple strategies and ensures isolated capital allocation.
"""

import logging
import asyncio
from datetime import datetime
from typing import Dict, List, Optional
from core.state_manager import StateManager

log = logging.getLogger("MultiStrategyManager")

class MultiStrategyManager:
    def __init__(self, state: StateManager, total_capital: float):
        self.state = state
        self.total_capital = total_capital
        
        # Default Allocations (can be overridden by config)
        self.allocations = {
            'scalper': 0.10,      # 10%
            'swing': 0.30,        # 30%
            'position': 0.50,     # 50%
            'ai_ensemble': 0.10   # 10%
        }
        
        # Per-strategy risk limits
        self.max_positions = {
            'scalper': 5,
            'swing': 3,
            'position': 2,
            'ai_ensemble': 2
        }

    async def get_active_trades(self, strategy: str) -> List[dict]:
        """Fetch active trades for a strategy from Redis."""
        key = f"strategy:trades:{strategy}"
        trades_raw = await self.state.get(key) or []
        return trades_raw

    async def can_open_trade(self, strategy: str, symbol: str, required_capital: float) -> bool:
        """
        Gating logic:
        1. Check strategy position count.
        2. Check strategy capital utilization.
        3. Check for direction conflicts (optional but recommended).
        """
        active_trades = await self.get_active_trades(strategy)
        
        # 1. Position Count Limit
        if len(active_trades) >= self.max_positions.get(strategy, 1):
            log.warning(f"🚫 {strategy} at max positions ({len(active_trades)})")
            return False
            
        # 2. Capital Limit
        allowed_pct = self.allocations.get(strategy, 0)
        strategy_total_cap = self.total_capital * allowed_pct
        current_utilized = sum(t.get('nominal_value', 0) for t in active_trades)
        
        if (current_utilized + required_capital) > strategy_total_cap:
            log.warning(f"🚫 {strategy} capital exhausted: {current_utilized}/{strategy_total_cap}")
            return False
            
        # 3. Symbol Conflict (Don't double up on the same symbol in one strategy)
        for t in active_trades:
            if t['symbol'] == symbol:
                log.warning(f"🚫 {strategy} already has active trade on {symbol}")
                return False
                
        return True

    async def register_trade(self, strategy: str, trade_data: dict):
        """Add a trade to the strategy tracking."""
        key = f"strategy:trades:{strategy}"
        trades = await self.get_active_trades(strategy)
        trade_data['start_time'] = datetime.utcnow().isoformat()
        trades.append(trade_data)
        await self.state.set(key, trades)
        log.info(f"💾 Registered {strategy} trade on {trade_data['symbol']}")

    async def remove_trade(self, strategy: str, symbol: str):
        """Remove a trade upon closure."""
        key = f"strategy:trades:{strategy}"
        trades = await self.get_active_trades(strategy)
        updated_trades = [t for t in trades if t['symbol'] != symbol]
        await self.state.set(key, updated_trades)
        log.info(f"🧹 Removed {strategy} trade on {symbol}")

    async def get_total_exposure(self) -> float:
        """Calculate total exposure across all strategies."""
        total = 0
        for strategy in self.allocations:
            trades = await self.get_active_trades(strategy)
            total += sum(t.get('nominal_value', 0) for t in trades)
        return total
