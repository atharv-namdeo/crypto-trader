import asyncio
import logging
import time
import json
import traceback
from core.state_manager import StateManager
from core.pnl_tracker import PnLTracker
from strategies.utils import compute_rsi, compute_vwap, compute_atr, compute_adx
from core.fuzzy_engine import FuzzyEngine

log = logging.getLogger("Swing")

def safe_last(value):
    """Get last value whether it's a Series or scalar"""
    if hasattr(value, 'iloc'):
        return float(value.iloc[-1])
    return float(value)

class SwingStrategy:
    def __init__(self, state: StateManager, pnl_tracker: PnLTracker, capital: float = 400.0):
        self.state = state
        self.pnl = pnl_tracker
        self.capital = capital
        self.symbols = ["BTC/USDT", "ETH/USDT"]
        self.running = False

    async def run_loop(self):
        self.running = True
        log.info(f"🌊 Start SWING Loop (Cap: ${self.capital})")
        while self.running:
            try:
                # Check if enabled in dashboard
                enabled = await self.state.get("settings:swing_enabled")
                if enabled == "false":
                    await asyncio.sleep(300)
                    continue

                for symbol in self.symbols:
                    await self._process(symbol)
            except asyncio.CancelledError:
                break
            except Exception as e:
                log.error(f"Swing error: {e}")
                log.error(traceback.format_exc())
            await asyncio.sleep(300)  # 5 minutes

    async def _process(self, symbol: str):
        df_1h = await self.state.get_df(f"ohlcv:1h:{symbol}", n=100)
        df_4h = await self.state.get_df(f"ohlcv:4h:{symbol}", n=100)
        price = await self.state.get_float(f"price:{symbol}")
        
        if df_1h is None or len(df_1h) < 50 or df_4h is None or len(df_4h) < 50 or not price:
            return

        pos = await self.state.get(f"swing:pos:{symbol}")
        
        # Compute indicators
        rsi_series_1h = compute_rsi(df_1h['close'], 14)
        rsi_val_1h = safe_last(rsi_series_1h)
        atr_1h = safe_last(compute_atr(df_1h, 14))
        ema50_4h = safe_last(df_4h['close'].ewm(span=50).mean())
        
        trend_up = price > ema50_4h
        
        if pos:
            side = pos['side']
            entry = pos['entry']
            qty = pos['qty']
            stop = pos['stop']
            tp = pos['tp']
            open_time = pos['time']
            elapsed_h = (time.time() - open_time) / 3600.0
            
            exit_reason = None
            if side == 'LONG':
                profit = price - entry
                # Trailing stop
                if profit > 1.5 * atr_1h and stop < entry + 0.5 * atr_1h:
                    pos['stop'] = entry + 0.5 * atr_1h
                    await self.state.set(f"swing:pos:{symbol}", pos)
                    
                if rsi_val_1h > 65: exit_reason = 'RSI_OVERBOUGHT'
                elif price > ema50_4h * 1.02: exit_reason = 'TARGET_4H'
                elif elapsed_h > 6: exit_reason = 'TIME_STOP'
                elif price >= tp: exit_reason = 'TAKE_PROFIT'
                elif price <= stop: exit_reason = 'STOP_LOSS'
            else:
                profit = entry - price
                if profit > 1.5 * atr_1h and stop > entry - 0.5 * atr_1h:
                    pos['stop'] = entry - 0.5 * atr_1h
                    await self.state.set(f"swing:pos:{symbol}", pos)
                    
                if rsi_val_1h < 35: exit_reason = 'RSI_OVERSOLD'
                elif price < ema50_4h * 0.98: exit_reason = 'TARGET_4H'
                elif elapsed_h > 6: exit_reason = 'TIME_STOP'
                elif price <= tp: exit_reason = 'TAKE_PROFIT'
                elif price >= stop: exit_reason = 'STOP_LOSS'
                
            if exit_reason:
                await self._close_position(symbol, pos, price, exit_reason)
                
        else:
            # Check concurrency limit
            active_holds = 0
            for sym in self.symbols:
                if await self.state.get(f"swing:pos:{sym}"):
                    active_holds += 1
            if active_holds >= 2:
                return

            fuzzy = FuzzyEngine()
            
            indicators = {
                'rsi':          rsi_val_1h,
                'price':        price,
                'vwap':         safe_last(compute_vwap(df_1h)),
                'vol_ratio':    df_1h['volume'].iloc[-1] / (safe_last(df_1h['volume'].rolling(20).mean()) + 1e-9),
                'adx':          safe_last(compute_adx(df_1h, 14)),
                'price_change': safe_last(df_1h['close'].pct_change(3)),
                'rsi_change':   safe_last(rsi_series_1h.diff(3)),
            }
            
            long_score  = fuzzy.compute_long_score(indicators)
            short_score = fuzzy.compute_short_score(indicators)
            
            # Fetch live threshold from Redis
            threshold = await self.state.get_float("settings:swing_threshold") or 0.55
            action, conviction = fuzzy.should_trade(long_score, short_score, 'SWING', threshold=threshold)
            
            # Store fuzzy scores for dashboard radar chart
            await self.state.set(f"fuzzy_scores:{symbol}", {
                "rsi": indicators['rsi'],
                "vwap": (df_1h['close'].iloc[-1] - indicators['vwap']) / indicators['vwap'] * 100,
                "vol": indicators['vol_ratio'],
                "adx": indicators['adx'],
                "long": long_score,
                "short": short_score
            })
            
            log.info(f"🧠 [SWING FUZZY] {symbol} long={long_score:.3f} short={short_score:.3f} → {action} (thresh={threshold})")
            
            if action == 'BUY' and trend_up:
                await self._open_position(symbol, 'LONG', price, atr_1h, conviction)
            elif action == 'SELL' and not trend_up:
                await self._open_position(symbol, 'SHORT', price, atr_1h, conviction)

    async def _open_position(self, symbol: str, side: str, price: float, atr: float, conviction: float):
        qty = (self.capital * 0.4) / price
        stop = price - 2.0 * atr if side == 'LONG' else price + 2.0 * atr
        tp = price + 4.0 * atr if side == 'LONG' else price - 4.0 * atr
        
        pos = {
            'side': side,
            'entry': price,
            'qty': qty,
            'stop': stop,
            'tp': tp,
            'time': time.time(),
            'strategy': 'SWING'
        }
        await self.state.set(f"swing:pos:{symbol}", pos)
        
        req = {'action': 'OPEN', 'side': side, 'qty': qty, 'price': price, 'stop': stop, 'tp': tp, 'strategy': 'SWING'}
        await self.state.set(f"order_request:{symbol}", req)

        # Record signal for dashboard
        signal = {
            'time': time.time(),
            'price': price,
            'type': 'LONG' if side == 'LONG' else 'SHORT',
            'action': 'OPEN',
            'strategy': 'SWING'
        }
        await self.state.redis.lpush('signals:history', json.dumps(signal))
        await self.state.redis.ltrim('signals:history', 0, 99)

        # Telegram notification
        from core.telegram_notifier import TelegramNotifier
        await TelegramNotifier().trade_opened('SWING', symbol, side, price, qty, stop, tp, conviction)

        log.info(f"🌊 [SWING] OPEN {side} {symbol} at {price:.2f}")

    async def _close_position(self, symbol: str, pos: dict, price: float, reason: str):
        # Calculate PNL
        entry = pos['entry']
        side = pos['side']
        qty = pos['qty']
        pnl_usd = (price - entry) * qty if side == 'LONG' else (entry - price) * qty

        await self.pnl.record_trade('SWING', symbol, side, entry, price, qty, reason)
        
        # Calculate duration
        duration_seconds = time.time() - pos.get('time', time.time())
        duration_str = f"{int(duration_seconds/3600)}h" if duration_seconds > 3600 else f"{int(duration_seconds/60)}m"

        # Telegram notification
        from core.telegram_notifier import TelegramNotifier
        await TelegramNotifier().trade_closed('SWING', symbol, side, entry, price, qty, pnl_usd, reason, duration_str)

        await self.state.redis.delete(f"swing:pos:{symbol}")
        
        req = {'action': 'CLOSE', 'side': pos['side'], 'qty': pos['qty'], 'strategy': 'SWING'}
        await self.state.set(f"order_request:{symbol}", req)
