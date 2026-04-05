import json
import logging
import numpy as np
from core.state_manager import StateManager

log = logging.getLogger("KellyCalc")

class KellyCalculator:
    """
    Quantitative risk modeling based on the Kelly Criterion.
    Optimizes position size to maximize long-term growth (geometric mean).
    """

    def __init__(self, state: StateManager):
        self.state = state
        self.min_trades = 10
        self.fractional_kelly = 0.25 # Quarter-Kelly (Conservative)
        self.min_risk_pct = 0.01    # Hard floor 1%
        self.max_risk_pct = 0.05    # Hard cap 5% per trade

    async def get_optimal_risk(self, strategy: str = "ai_ensemble") -> float:
        """
        Calculates optimal risk percentage for a strategy based on its history.
        Formula: K% = W - ((1 - W) / R)
        Where W = Win Rate, R = Profit/Loss Ratio
        """
        try:
            # 1. Fetch History from Redis
            history_raw = await self.state.redis.lrange('trade:history', 0, 99)
            if not history_raw:
                return 0.015 # Default 1.5% if no history

            trades = [json.loads(t) for t in history_raw if json.loads(t).get('strategy', '').lower() == strategy.lower()]
            
            if len(trades) < self.min_trades:
                log.info(f"Kelly: Not enough trades ({len(trades)} < {self.min_trades}). Using default 1.5%")
                return 0.015

            # 2. Extract PnL stats
            # We use pnl_net which already accounts for fees
            pnls = [t.get('pnl_net', t.get('pnl', 0)) for t in trades]
            
            wins = [p for p in pnls if p > 0]
            losses = [p for p in pnls if p <= 0]
            
            if not losses: return self.max_risk_pct
            if not wins: return 0.005 # 0.5% if losing everything
            
            win_rate = len(wins) / len(pnls)
            avg_win = np.mean(wins)
            avg_loss = abs(np.mean(losses))
            
            win_loss_ratio = avg_win / (avg_loss + 1e-9)
            
            # 3. Kelly Formula
            kelly_full = win_rate - ((1 - win_rate) / win_loss_ratio)
            
            # 4. Apply Fractional Kelly and Constraints
            risk_pct = kelly_full * self.fractional_kelly
            risk_pct = max(self.min_risk_pct, min(risk_pct, self.max_risk_pct))
            
            log.info(f"📊 Kelly for {strategy}: WR={win_rate:.1%}, R={win_loss_ratio:.2f} -> K%={risk_pct:.2%}")
            return risk_pct

        except Exception as e:
            log.error(f"Error calculating Kelly: {e}")
            return 0.01

    async def get_drawdown_multiplier(self) -> float:
        """
        Graduated Drawdown Response.
        Reduces sizing as equity drops from peak.
        """
        try:
            peak = await self.state.get_float('metrics:peak_equity') or 1000.0
            current = await self.state.get_float('portfolio:value') or 1000.0
            
            drawdown = (peak - current) / peak
            
            if drawdown < 0.02: return 1.0    # No reduction up to 2% DD
            if drawdown < 0.05: return 0.75   # 25% reduction
            if drawdown < 0.10: return 0.5    # 50% reduction
            return 0.25                      # 75% reduction above 10% DD
            
        except Exception:
            return 1.0
