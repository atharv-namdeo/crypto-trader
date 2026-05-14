import logging
import json
import asyncio
from core.state_manager import StateManager

log = logging.getLogger("AutoTuner")

class StrategyAutoTuner:
    """
    Automatically optimize strategy thresholds based on live performance.
    Example: Find optimal RSI or Threshold values for strategies.
    """
    
    def __init__(self, state: StateManager):
        self.state = state
    
    async def optimize_thresholds(self, symbol: str, strategy: str):
        """
        Analyze recent trade history and adjust strategy parameters.
        """
        # 1. Fetch recent trades for this strategy/symbol
        trades_raw = await self.state.redis.lrange(f'trade:history', 0, 49)
        if not trades_raw:
            return
            
        trades = [json.loads(t) for t in trades_raw if json.loads(t).get('strategy') == strategy]
        
        if len(trades) < 5:
            return # Need more data for optimization
            
        # 2. Split into winners and losers
        winners = [t for t in trades if t.get('pnl', 0) > 0]
        losers = [t for t in trades if t.get('pnl', 0) <= 0]
        
        if not winners:
            log.info(f"No winners found for {strategy} on {symbol}. Reviewing thresholds...")
            # If consistent losses, increase threshold to be more selective
            current_threshold = await self.state.get_float(f'settings:{strategy}_threshold') or 0.5
            new_threshold = min(0.85, current_threshold + 0.05)
            await self.state.set(f'settings:{strategy}_threshold', new_threshold)
            return
            
        # 3. Simple Optimization: Check average confidence of winners
        avg_win_conf = sum(t.get('confidence', 0) for t in winners) / len(winners)
        avg_loss_conf = sum(t.get('confidence', 0) for t in losers) / len(losers) if losers else 0
        
        # If winners have significantly higher confidence, adjust threshold
        if avg_win_conf > avg_loss_conf + 0.10:
            # Set threshold slightly below average winning confidence
            new_threshold = max(0.40, avg_win_conf - 0.05)
            await self.state.set(f'settings:{strategy}_threshold', new_threshold)
            log.info(f"🔧 Optimized {strategy} threshold to {new_threshold:.2f} based on winners.")
            
    async def run_periodic_tuning(self, symbols: list):
        """Background task to tune all strategies daily"""
        while True:
            try:
                for symbol in symbols:
                    for strategy in ["scalper", "swing", "position", "ai_ensemble"]:
                        await self.optimize_thresholds(symbol, strategy)
                        
                # Wait 24 hours
                await asyncio.sleep(86400)
            except Exception as e:
                log.error(f"AutoTuner error: {e}")
                await asyncio.sleep(3600)
