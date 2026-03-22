import json
import logging
from datetime import datetime
from core.state_manager import StateManager
from config import CAPITAL

log = logging.getLogger("PnLTracker")

class PnLTracker:
    def __init__(self, state: StateManager):
        self.state = state
        self.log = log

    async def record_trade(self, strategy: str, symbol: str, side: str, entry: float, exit_price: float, qty: float, reason: str):
        pnl_usd = (exit_price - entry) * qty if side == 'LONG' else (entry - exit_price) * qty
        
        # Update portfolio value
        portfolio = await self.state.get_float('portfolio:value') or float(CAPITAL)
        portfolio += pnl_usd
        await self.state.set('portfolio:value', portfolio)
        
        # Record in trade history
        trade = {
            'strategy': strategy,
            'symbol': symbol,
            'side': side,
            'entry': entry,
            'exit': exit_price,
            'qty': qty,
            'pnl': pnl_usd,
            'reason': reason,
            'time': datetime.utcnow().isoformat()
        }
        
        try:
            await self.state.redis.lpush('trade:history', json.dumps(trade))
            await self.state.redis.ltrim('trade:history', 0, 499)  # keep last 500
        except Exception as e:
            self.log.error(f"Redis trade log error: {e}")
            
        try:
            await self.state.redis.incrbyfloat('pnl:24h', pnl_usd)
        except Exception:
            pass
            
        self.log.info(f"[PnL] {strategy} {side} {symbol}: "
                      f"entry={entry:.2f} exit={exit_price:.2f} "
                      f"pnl=${pnl_usd:.4f} portfolio=${portfolio:.2f}")

        # Sync exactly with Firebase Dashboard
        try:
            from utils.firebase_client import log_trade
            log_trade({
                'symbol': symbol,
                'direction': side,
                'entry': entry,
                'exit': exit_price,
                'qty': qty,
                'pnl': pnl_usd,
                'strategy': strategy
            })
        except Exception as e:
            self.log.warning(f"Could not sync closed trade to dashboard: {e}")
