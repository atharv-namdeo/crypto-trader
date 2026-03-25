import asyncio
import json
import logging
import time
from datetime import datetime
from core.state_manager import StateManager

log = logging.getLogger("DashboardSync")

class DashboardSynchronizer:
    def __init__(self, state: StateManager):
        self.state = state
        self.running = False

    async def run_loop(self, interval: int = 1):
        self.running = True
        log.info(f"🔄 Dashboard Synchronizer Started (Interval: {interval}s)")
        
        while self.running:
            try:
                await self._sync_active_positions()
                await self._sync_strategy_stats()
                await self._sync_portfolio_metrics()
            except Exception as e:
                log.error(f"Dashboard sync error: {e}")
            
            await asyncio.sleep(interval)

    async def _sync_active_positions(self):
        """Aggregate all strategy-specific positions into a single Redis list."""
        if not self.state.redis:
            return

        all_positions = []
        strategies = ["scalper", "swing", "position", "ai_ensemble"]
        
        for s in strategies:
            # Pattern: {strategy}:pos:{symbol}
            keys = await self.state.redis.keys(f"{s}:pos:*")
            for key in keys:
                pos_data = await self.state.get(key)
                if pos_data:
                    # Add strategy metadata if missing
                    if isinstance(pos_data, dict):
                        pos_data['strategy'] = s.upper()
                        # Calculate unrealized PnL if possible
                        symbol = pos_data.get('symbol')
                        if symbol:
                            price = await self.state.get_float(f"price:{symbol}")
                            if price and 'entry' in pos_data:
                                entry = pos_data['entry']
                                side = pos_data.get('side', 'LONG')
                                pnl = (price - entry) if side == 'LONG' else (entry - price)
                                pos_data['unrealized_pnl'] = pnl * pos_data.get('qty', 0)
                                pos_data['unrealized_pnl_pct'] = (pnl / entry * 100)
                        all_positions.append(pos_data)

        # Store in positions:active for the API to read
        await self.state.set("positions:active", all_positions)
        
        # Update pos_count for each strategy
        for s in strategies:
            count = sum(1 for p in all_positions if p.get('strategy') == s.upper())
            await self.state.set(f"stats:{s}:pos_count", count)

    async def _sync_strategy_stats(self):
        """Ensure all strategy stats have baseline values."""
        for s in ["scalper", "swing", "position", "ai_ensemble"]:
            s_base = f"stats:{s}"
            # trades, wins, pnl are updated by PnLTracker, but we ensure they exist
            if await self.state.get(f"{s_base}:trades") is None:
                await self.state.set(f"{s_base}:trades", 0)
            if await self.state.get(f"{s_base}:wins") is None:
                await self.state.set(f"{s_base}:wins", 0)
            if await self.state.get(f"{s_base}:pnl") is None:
                await self.state.set(f"{s_base}:pnl", 0.0)

    async def _sync_portfolio_metrics(self):
        """Sync various portfolio-level metrics."""
        # Sync portfolio:total_value with portfolio:value (standardizing names)
        val = await self.state.get_float("portfolio:value")
        if val:
            await self.state.set("portfolio:total_value", val)
        
        # Calculate aggregate daily PnL from trade history if not already tracked
        # (Though PnLTracker handles this, we can verify or add extra metrics here)
        pass

    def stop(self):
        self.running = False
