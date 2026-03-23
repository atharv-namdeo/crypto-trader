import asyncio
import logging
import time
import json
import traceback
from core.state_manager import StateManager
from core.pnl_tracker import PnLTracker
from strategies.utils import compute_rsi, compute_vwap, compute_atr, compute_adx
from core.fuzzy_engine import FuzzyEngine

log = logging.getLogger("Scalper")

def safe_last(value):
    """Get last value whether it's a Series or scalar"""
    if hasattr(value, 'iloc'):
        return float(value.iloc[-1])
    return float(value)

class ScalperStrategy:
    def __init__(self, state: StateManager, pnl_tracker: PnLTracker, capital: float = 200.0):
        self.state = state
        self.pnl = pnl_tracker
        self.capital = capital
        self.symbols = ["BTC/USDT", "ETH/USDT"]
        self.running = False

    async def run_loop(self):
        self.running = True
        log.info(f"⚡ Start SCALPER Loop (Cap: ${self.capital})")
        while self.running:
            try:
                # Check if enabled in dashboard
                enabled = await self.state.get("settings:scalper_enabled")
                if enabled == "false":
                    await asyncio.sleep(30)
                    continue

                for symbol in self.symbols:
                    await self._process(symbol)
            except asyncio.CancelledError:
                break
            except Exception as e:
                log.error(f"Scalper error: {e}")
                log.error(traceback.format_exc())
            await asyncio.sleep(30)

    async def _process(self, symbol: str):
        df_1m = await self.state.get_df(f"ohlcv:1m:{symbol}", n=100)
        price = await self.state.get_float(f"price:{symbol}")
        if df_1m is None or len(df_1m) < 20 or not price:
            return

        pos = await self.state.get(f"scalper:pos:{symbol}")
        
        # Compute indicators
        rsi_series = compute_rsi(df_1m['close'], 7)
        rsi_1m = safe_last(rsi_series)
        
        vwap_raw = compute_vwap(df_1m)
        vwap = safe_last(vwap_raw)
        
        vol_sma = safe_last(df_1m['volume'].rolling(10).mean())
        vol_ratio = df_1m['volume'].iloc[-1] / (vol_sma + 1e-9)
        atr_1m = safe_last(compute_atr(df_1m, 14))
        
        if pos:
            # Check exit logic
            side = pos['side']
            entry = pos['entry']
            qty = pos['qty']
            open_time = pos['time']
            elapsed_m = (time.time() - open_time) / 60.0
            
            exit_reason = None
            if side == 'LONG':
                if rsi_1m >= 50: exit_reason = 'RSI_REVERSION'
                elif price >= vwap: exit_reason = 'VWAP_TARGET'
                elif elapsed_m > 15: exit_reason = 'TIME_STOP'
                elif price < entry - (0.8 * atr_1m): exit_reason = 'STOP_LOSS'
            else:
                if rsi_1m <= 50: exit_reason = 'RSI_REVERSION'
                elif price <= vwap: exit_reason = 'VWAP_TARGET'
                elif elapsed_m > 15: exit_reason = 'TIME_STOP'
                elif price > entry + (0.8 * atr_1m): exit_reason = 'STOP_LOSS'
                
            if exit_reason:
                await self._close_position(symbol, pos, price, exit_reason)
                
        else:
            # Check entry logic
            active_holds = 0
            for sym in self.symbols:
                if await self.state.get(f"scalper:pos:{sym}"):
                    active_holds += 1
            
            if active_holds >= 2:
                return # max concurrent positions reached

            fuzzy = FuzzyEngine()
            
            indicators = {
                'rsi':          rsi_1m,
                'price':        price,
                'vwap':         vwap,
                'vol_ratio':    vol_ratio,
                'adx':          safe_last(compute_adx(df_1m, 7)),
                'price_change': safe_last(df_1m['close'].pct_change(3)),
                'rsi_change':   safe_last(rsi_series.diff(3)),
            }
            
            long_score  = fuzzy.compute_long_score(indicators)
            short_score = fuzzy.compute_short_score(indicators)
            
            # Fetch live threshold from Redis
            threshold = await self.state.get_float("settings:scalper_threshold") or 0.45
            action, conviction = fuzzy.should_trade(long_score, short_score, 'SCALPER', threshold=threshold)
            
            # Store fuzzy scores for dashboard radar chart
            await self.state.set(f"fuzzy_scores:{symbol}", {
                "rsi": indicators['rsi'],
                "vwap": (df_1m['close'].iloc[-1] - indicators['vwap']) / indicators['vwap'] * 100,
                "vol": indicators['vol_ratio'],
                "adx": indicators['adx'],
                "long": long_score,
                "short": short_score
            })
            
            log.info(f"🧠 [SCALPER FUZZY] {symbol} long={long_score:.3f} short={short_score:.3f} → {action} (thresh={threshold})")
            
            if action == 'BUY':
                await self._open_position(symbol, 'LONG', price, conviction)
            elif action == 'SELL':
                await self._open_position(symbol, 'SHORT', price, conviction)

    async def _open_position(self, symbol: str, side: str, price: float, conviction: float):
        qty = (self.capital * 0.5) / price
        pos = {
            'side': side,
            'entry': price,
            'qty': qty,
            'time': time.time(),
            'strategy': 'SCALPER'
        }
        await self.state.set(f"scalper:pos:{symbol}", pos)
        
        # Send physical order request to Binance 
        req = {'action': 'OPEN', 'side': side, 'qty': qty, 'price': price, 'stop': 0, 'tp': 0, 'strategy': 'SCALPER'}
        await self.state.set(f"order_request:{symbol}", req)
        
        # Record signal for dashboard
        signal = {
            'time': time.time(),
            'price': price,
            'type': 'LONG' if side == 'LONG' else 'SHORT',
            'action': 'OPEN',
            'strategy': 'SCALPER'
        }
        await self.state.redis.lpush('signals:history', json.dumps(signal))
        await self.state.redis.ltrim('signals:history', 0, 99)

        # Telegram notification
        from core.telegram_notifier import TelegramNotifier
        await TelegramNotifier().trade_opened('SCALPER', symbol, side, price, qty, 0, 0, conviction)
        
        log.info(f"⚡ [SCALPER] OPEN {side} {symbol} at {price:.2f}")

    async def _close_position(self, symbol: str, pos: dict, price: float, reason: str):
        # Calculate PNL
        entry = pos['entry']
        side = pos['side']
        qty = pos['qty']
        pnl_usd = (price - entry) * qty if side == 'LONG' else (entry - price) * qty
        
        await self.pnl.record_trade('SCALPER', symbol, side, entry, price, qty, reason)
        
        # Calculate duration
        duration_seconds = time.time() - pos.get('time', time.time())
        duration_str = f"{int(duration_seconds/60)}m" if duration_seconds < 3600 else f"{duration_seconds/3600:.1f}h"

        # Telegram notification
        from core.telegram_notifier import TelegramNotifier
        await TelegramNotifier().trade_closed('SCALPER', symbol, side, entry, price, qty, pnl_usd, reason, duration_str)

        # Clear local state
        await self.state.redis.delete(f"scalper:pos:{symbol}")
        
        # Send physical close to Binance
        req = {'action': 'CLOSE', 'side': pos['side'], 'qty': pos['qty'], 'strategy': 'SCALPER'}
        await self.state.set(f"order_request:{symbol}", req)
