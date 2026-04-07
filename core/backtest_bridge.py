import pandas as pd
import logging
import json
from datetime import datetime
from backtest_pro import ExpertBacktestEngine, DataFetcher

log = logging.getLogger("BT-BRIDGE")

class BacktestBridge:
    def __init__(self):
        self.fetcher = DataFetcher()

    async def execute_audit(self, symbol: str, start_date: str, end_date: str, initial_capital: float = 10000.0):
        """Programmatic entry point for Dashboard Backtesting."""
        log.info(f"🚀 Integrated Audit Started: {symbol} | {start_date} -> {end_date}")
        
        try:
            # 1. Fetch High-Fidelity OHLCV Data
            df_m, df_h = self.fetcher.fetch_all(symbol, start_date, end_date)
            if df_m is None or df_m.empty:
                return {"status": "error", "message": "Historical Liquidity Not Found"}

            # 2. Initialize Hardened Grandmaster Engine (v11.1.4)
            engine = ExpertBacktestEngine(initial_capital=initial_capital)
            
            # 3. Synchronous Simulation (FastAPI runs this in persistent threadpool)
            engine.run_backtest(df_m, df_h, btc_h=None) # BTC default to internal fetch
            
            # 4. Process Results for Recharts Visualization
            # Sample equity curve for every 100 steps to keep JSON small
            equity_history = []
            final_cap = engine.capital
            
            # Generate a time-series equity curve from trade history
            # (Note: In a more advanced version, we'd track candle-by-candle equity)
            curr_cap = initial_capital
            equity_history.append({"time": start_date, "balance": curr_cap})
            
            for t in engine.trades:
                curr_cap += t['pnl_net']
                equity_history.append({
                    "time": t['time'].isoformat() if hasattr(t['time'], 'isoformat') else str(t['time']),
                    "balance": round(curr_cap, 2)
                })

            # Calculate Final Statistics
            pnl_usd = final_cap - initial_capital
            pnl_pct = (pnl_usd / initial_capital) * 100
            wins = sum(1 for t in engine.trades if t['pnl_net'] > 0)
            win_rate = (wins / len(engine.trades) * 100) if engine.trades else 0
            
            return {
                "status": "success",
                "metrics": {
                    "initial": initial_capital,
                    "final": round(final_cap, 2),
                    "pnl_usd": round(pnl_usd, 2),
                    "pnl_pct": round(pnl_pct, 2),
                    "win_rate": round(win_rate, 2),
                    "total_trades": len(engine.trades),
                },
                "equity_curve": equity_history,
                "trades": [
                    {
                        "time": t['time'].isoformat() if hasattr(t['time'], 'isoformat') else str(t['time']),
                        "side": t['side'],
                        "pnl": round(t['pnl_net'], 2),
                        "reason": t['reason'],
                        "regime": t['regime']
                    } for t in engine.trades[-20:] # Return last 20 for log
                ]
            }

        except Exception as e:
            log.error(f"Audit failure: {e}")
            return {"status": "error", "message": str(e)}

    def run_sync(self, symbol: str, start_date: str, end_date: str, initial_capital: float = 10000.0):
        """Wrapper for non-async execution in background threads."""
        import asyncio
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        return loop.run_until_complete(self.execute_audit(symbol, start_date, end_date, initial_capital))
