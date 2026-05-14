import pandas as pd
import logging
from datetime import datetime, timezone
import ccxt.async_support as ccxt
from core.strategies.ensemble_algorithm import EnsembleAlgorithm
from core.risk import RiskManager

log = logging.getLogger("BacktestEngine")

class BacktestEngine:
    """Runs historical replays and returns formatted trade results."""
    
    def __init__(self, state_manager, risk_manager):
        self.state = state_manager
        self.risk  = risk_manager
        self.exchange = ccxt.binance({"enableRateLimit": True})

    async def run_day_backtest(self, date_str: str, symbols: list):
        """Replays a specific 24-hour period."""
        log.info(f"📅 Replaying market for {date_str}...")
        
        start_ms = self.exchange.parse8601(f"{date_str}T00:00:00Z")
        end_ms = start_ms + (24 * 3600 * 1000)
        
        results = []
        
        for symbol in symbols:
            trades = await self._replay_symbol(symbol, start_ms, end_ms)
            results.extend(trades)
            
        return results

    async def _replay_symbol(self, symbol: str, start_ms: int, end_ms: int):
        """Simulates 1h candle strategy entries and 1m candle exits."""
        # 1. Fetch data for the day
        # We need some warmup data for indicators (EMA200, etc)
        warmup_start = start_ms - (100 * 3600 * 1000) # 100 hours warmup
        
        try:
            ohlcv_1h = await self.exchange.fetch_ohlcv(symbol, '1h', since=warmup_start, limit=200)
            ohlcv_1m = await self.exchange.fetch_ohlcv(symbol, '1m', since=start_ms, limit=1440)
            
            if not ohlcv_1h or not ohlcv_1m: return []
            
            df_1h = pd.DataFrame(ohlcv_1h, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
            df_1m = pd.DataFrame(ohlcv_1m, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
            
            # 2. Replay loop (hour by hour)
            trades = []
            active_trade = None
            
            # Strategy Engine
            engine = EnsembleAlgorithm(state_manager=None) # We'll mock state
            
            day_candles_1h = df_1h[df_1h['timestamp'] >= start_ms]
            
            for _, row in day_candles_1h.iterrows():
                ts = row['timestamp']
                
                # Point-in-time slice for engine
                pit_df = df_1h[df_1h['timestamp'] <= ts].tail(200)
                
                # Check for entry if no active trade
                if not active_trade:
                    # Mock state's get_df for the engine
                    # (This is a bit tricky since EnsembleAlgorithm expects a StateManager)
                    # For this replay, we'll manually check the signal logic
                    signal = await self._check_signal(symbol, pit_df)
                    
                    if signal["action"] != "NEUTRAL":
                        entry_price = row['close']
                        # Calculate stops
                        atr = row['high'] - row['low'] # Simple ATR
                        stops = self.risk.calculate_adaptive_stops(entry_price, atr, "BULL", signal["action"])
                        
                        active_trade = {
                            "symbol": symbol,
                            "side": "LONG" if signal["action"] == "BUY" else "SHORT",
                            "entry": entry_price,
                            "sl": stops["stop"],
                            "tp": stops["tp"],
                            "opened_at": ts
                        }
                
                # If active trade, check for exit in 1m candles for this hour
                if active_trade:
                    hour_end = ts + (3600 * 1000)
                    m_candles = df_1m[(df_1m['timestamp'] >= ts) & (df_1m['timestamp'] < hour_end)]
                    
                    for _, m_row in m_candles.iterrows():
                        exit_price, reason = self._check_exit(active_trade, m_row)
                        if exit_price:
                            # Settle
                            pnl = self._calc_pnl(active_trade, exit_price)
                            trades.append({
                                "symbol": symbol,
                                "side": active_trade["side"],
                                "entry": active_trade["entry"],
                                "exit": exit_price,
                                "pnl_pct": pnl,
                                "pnl_val": pnl * 100, # Assuming $1000 size for replay
                                "reason": f"{reason} (Replay)",
                                "closed_at": m_row['timestamp']
                            })
                            active_trade = None
                            break
                            
            return trades

        except Exception as e:
            log.error(f"Error replaying {symbol}: {e}")
            return []

    async def _check_signal(self, symbol, df):
        """Simplified signal check for replay."""
        # Use simple crossover for replay demo
        close = df['close']
        ema9 = close.ewm(span=9).mean().iloc[-1]
        ema21 = close.ewm(span=21).mean().iloc[-1]
        
        if ema9 > ema21: return {"action": "BUY"}
        if ema9 < ema21: return {"action": "SELL"}
        return {"action": "NEUTRAL"}

    def _check_exit(self, trade, candle):
        side = trade["side"]
        sl = trade["sl"]
        tp = trade["tp"]
        if side == "LONG":
            if candle['low'] <= sl: return sl, "STOP_LOSS"
            if candle['high'] >= tp: return tp, "TAKE_PROFIT"
        else:
            if candle['high'] >= sl: return sl, "STOP_LOSS"
            if candle['low'] <= tp: return tp, "TAKE_PROFIT"
        return None, None

    def _calc_pnl(self, trade, exit_price):
        entry = trade["entry"]
        if trade["side"] == "LONG":
            return (exit_price - entry) / entry
        return (entry - exit_price) / entry

    async def close(self):
        await self.exchange.close()
