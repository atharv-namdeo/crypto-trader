import json
import logging
import numpy as np
from datetime import datetime
from core.state_manager import StateManager
from config import CAPITAL

log = logging.getLogger("PnLTracker")

class PnLTracker:
    def __init__(self, state: StateManager):
        self.state = state
        self.log = log

    async def record_trade(self, strategy: str, symbol: str, side: str, entry: float, exit_price: float, qty: float, reason: str):
        # 1. Calculate Costs (Binance Futures Default: 0.04% Taker)
        fee_rate = 0.0004
        entry_notional = entry * qty
        exit_notional = exit_price * qty
        total_fees = (entry_notional + exit_notional) * fee_rate
        
        # 2. PnL Calculation
        pnl_gross = (exit_price - entry) * qty if side == 'LONG' else (entry - exit_price) * qty
        pnl_net = pnl_gross - total_fees
        is_win = pnl_net > 0
        
        # Update portfolio value (using NET PnL)
        portfolio = await self.state.get_float('portfolio:value') or float(CAPITAL)
        portfolio += pnl_net
        await self.state.set('portfolio:value', portfolio)
        
        # Strategy-Specific Stats
        s_base = f"stats:{strategy.lower()}"
        await self.state.redis.incr(f"{s_base}:trades")
        if is_win:
            await self.state.redis.incr(f"{s_base}:wins")
        await self.state.redis.incrbyfloat(f"{s_base}:pnl", pnl_net)
        await self.state.redis.incrbyfloat(f"{s_base}:fees", total_fees)
        
        # Equity History
        equity_entry = {
            'time': datetime.utcnow().strftime('%H:%M:%S'),
            'value': portfolio,
            'strategy': strategy
        }
        await self.state.redis.lpush('equity:history', json.dumps(equity_entry))
        await self.state.redis.ltrim('equity:history', 0, 100)
        
        # Record in trade history
        trade = {
            'strategy': strategy,
            'symbol': symbol,
            'side': side,
            'entry': entry,
            'exit': exit_price,
            'qty': qty,
            'pnl_gross': pnl_gross,
            'pnl_net': pnl_net,
            'fees': total_fees,
            'reason': reason,
            'time': datetime.utcnow().isoformat()
        }
        
        try:
            await self.state.redis.lpush('trade:history', json.dumps(trade))
            await self.state.redis.ltrim('trade:history', 0, 499)
            
            # Log signal for chart
            signal = {
                'time': datetime.utcnow().timestamp(),
                'price': exit_price,
                'type': side,
                'action': 'CLOSE',
                'strategy': strategy,
                'pnl': pnl_usd
            }
            await self.state.redis.lpush('signals:history', json.dumps(signal))
            await self.state.redis.ltrim('signals:history', 0, 99)
        except Exception as e:
            self.log.error(f"Redis trade log error: {e}")
            
        await self._update_metrics(pnl_usd, portfolio)
            
        self.log.info(f"[PnL] {strategy} {side} {symbol}: "
                      f"entry={entry:.2f} exit={exit_price:.2f} "
                      f"pnl=${pnl_usd:.4f} portfolio=${portfolio:.2f}")

        # Sync with Firebase Dashboard
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

    async def _update_metrics(self, last_pnl, current_portfolio):
        """Compute Sharpe, Drawdown, Profit Factor and store in Redis"""
        try:
            # 1. Store return for Sharpe
            ret = last_pnl / (current_portfolio - last_pnl + 1e-9)
            await self.state.redis.lpush('metrics:returns', ret)
            await self.state.redis.ltrim('metrics:returns', 0, 100)
            
            # Sharpe calculation
            returns_raw = await self.state.redis.lrange('metrics:returns', 0, -1)
            returns = [float(r) for r in returns_raw]
            if len(returns) > 5:
                mean = np.mean(returns)
                std = np.std(returns)
                sharpe = (mean / (std + 1e-9)) * np.sqrt(365 * 24) # annualized from hourly-ish cycles
                await self.state.set('metrics:sharpe', round(sharpe, 2))

            # 2. Drawdown
            peak = await self.state.get_float('metrics:peak_equity') or float(CAPITAL)
            if current_portfolio > peak:
                peak = current_portfolio
                await self.state.set('metrics:peak_equity', peak)
            
            drawdown = (peak - current_portfolio) / peak * 100
            await self.state.set('metrics:drawdown', round(drawdown, 2))

            # 3. Profit Factor
            await self.state.redis.incrbyfloat('metrics:gross_profit' if last_pnl > 0 else 'metrics:gross_loss', abs(last_pnl))
            gp = await self.state.get_float('metrics:gross_profit') or 0
            gl = await self.state.get_float('metrics:gross_loss') or 0
            pf = gp / (gl + 1e-9)
            await self.state.set('metrics:profit_factor', round(pf, 2))

            # 4. Win Rate
            trades = await self.state.redis.lrange('trade:history', 0, -1)
            if trades:
                wins = sum(1 for t in trades if json.loads(t).get('pnl', 0) > 0)
                await self.state.set('metrics:winrate', round((wins / len(trades)) * 100, 1))

        except Exception as e:
            self.log.error(f"Error updating metrics: {e}")
