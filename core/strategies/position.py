import asyncio
import logging
import time
import json
import traceback
from core.state_manager import StateManager
from core.pnl_tracker import PnLTracker
from core.utils import compute_rsi, compute_vwap, compute_atr, compute_adx
from core.fuzzy_engine import FuzzyEngine
from config import SYMBOLS

log = logging.getLogger("PositionTrader")

def safe_last(value):
    """Get last value whether it's a Series or scalar"""
    if hasattr(value, 'iloc'):
        return float(value.iloc[-1])
    return float(value)

class PositionStrategy:
    def __init__(self, state: StateManager, pnl_tracker: PnLTracker, capital: float = 400.0):
        self.state = state
        self.pnl = pnl_tracker
        self.capital = capital
        self.symbols = SYMBOLS
        self.running = False

    async def run_loop(self):
        self.running = True
        log.info(f"🏔️ Start POSITION Loop (Cap: ${self.capital})")
        while self.running:
            try:
                # Check if enabled in dashboard
                enabled = await self.state.get("settings:position_enabled")
                if enabled == "false":
                    await asyncio.sleep(900)
                    continue

                for symbol in self.symbols:
                    await self._process(symbol)
            except asyncio.CancelledError:
                break
            except Exception as e:
                log.error(f"PositionTrader error: {e}")
                log.error(traceback.format_exc())
            await asyncio.sleep(900)  # 15 minutes

    async def _process(self, symbol: str):
        df_4h = await self.state.get_df(f"ohlcv:4h:{symbol}", n=100)
        df_1d = await self.state.get_df(f"ohlcv:1d:{symbol}", n=100) # Assuming 1d exists or fallback 
        price = await self.state.get_float(f"price:{symbol}")
        
        # Note: If 1d is missing from live feed, compute it down-sampled from 4h or just skip for now
        # The user feed logic doesn't explicitly save `1d` natively, so let's safely downsample 4h if missing
        if df_4h is None or len(df_4h) < 60 or not price:
            return
            
        if df_1d is None:
            # Mock 1d from 4h
            df_1d = df_4h.iloc[::6].copy()
            if len(df_1d) < 20: return

        pos = await self.state.get(f"position:pos:{symbol}")
        
        adx_4h = safe_last(compute_adx(df_4h, 14))
        strong_trend = adx_4h > 25
        
        ema20_1d = safe_last(df_1d['close'].ewm(span=20).mean())
        ema50_1d = safe_last(df_1d['close'].ewm(span=50).mean())
        daily_bull = ema20_1d > ema50_1d
        
        vol_increasing = df_4h['volume'].iloc[-3:].mean() > df_4h['volume'].iloc[-10:-3].mean()
        
        structure = 'NEUTRAL'
        if daily_bull and strong_trend and vol_increasing:
            structure = 'BULL'
        elif not daily_bull and strong_trend and vol_increasing:
            structure = 'BEAR'
            
        atr_4h = safe_last(compute_atr(df_4h, 14))
        
        if pos:
            side = pos['side']
            entry = pos['entry']
            qty = pos['qty']
            stop = pos['stop']
            tp1 = pos['tp1']
            tp2 = pos['tp2']
            open_time = pos['time']
            highest = pos.get('highest', entry)
            lowest = pos.get('lowest', entry)
            
            elapsed_h = (time.time() - open_time) / 3600.0
            exit_reason = None
            
            if side == 'LONG':
                highest = max(highest, price)
                # Trailing stop after TP1
                if price >= tp1 and pos.get('state') == 'FULL':
                    # Partial close TP1
                    await self._close_partial(symbol, pos, price, qty * 0.5, 'TP1_HIT')
                    pos['state'] = 'PARTIAL'
                    pos['qty'] = qty * 0.5
                    pos['stop'] = entry # move stop to breakeven
                    
                if pos.get('state') == 'PARTIAL':
                    # Trail stop 1.5 ATR from highest close
                    trail = highest - 1.5 * atr_4h
                    if trail > pos['stop']: pos['stop'] = trail
                    
                pos['highest'] = highest
                await self.state.set(f"position:pos:{symbol}", pos)
                
                if price >= tp2: exit_reason = 'TP2_HIT'
                elif price <= pos['stop']: exit_reason = 'STOP_LOSS'
                elif elapsed_h > 24: exit_reason = 'TIME_STOP'
                
            else:
                lowest = min(lowest, price)
                if price <= tp1 and pos.get('state') == 'FULL':
                    await self._close_partial(symbol, pos, price, qty * 0.5, 'TP1_HIT')
                    pos['state'] = 'PARTIAL'
                    pos['qty'] = qty * 0.5
                    pos['stop'] = entry
                    
                if pos.get('state') == 'PARTIAL':
                    trail = lowest + 1.5 * atr_4h
                    if trail < pos['stop']: pos['stop'] = trail
                    
                pos['lowest'] = lowest
                await self.state.set(f"position:pos:{symbol}", pos)
                
                if price <= tp2: exit_reason = 'TP2_HIT'
                elif price >= pos['stop']: exit_reason = 'STOP_LOSS'
                elif elapsed_h > 24: exit_reason = 'TIME_STOP'
                
            if exit_reason:
                await self._close_position(symbol, pos, price, exit_reason)

        else:
            active_holds = len(await self.state.redis.keys("position:pos:*"))
            if active_holds >= 1:
                return

            rsi_series_4h = compute_rsi(df_4h['close'], 14)
            rsi_4h_val = safe_last(rsi_series_4h)
            fuzzy = FuzzyEngine()
            
            # Fetch ML Filter (from central main.py loop)
            ml_pred = await self.state.get(f"ml_signal:{symbol}")
            ml_dir = 'HOLD'
            if ml_pred:
                ml_dir = ml_pred.get('signal', 'HOLD')
                ml_conf = ml_pred.get('confidence', 0.5)
            indicators = {
                'rsi':          rsi_4h_val,
                'price':        price,
                'vwap':         safe_last(compute_vwap(df_4h)),
                'vol_ratio':    df_4h['volume'].iloc[-1] / (safe_last(df_4h['volume'].rolling(20).mean()) + 1e-9),
                'adx':          adx_4h,
                'price_change': safe_last(df_4h['close'].pct_change(3)),
                'rsi_change':   safe_last(rsi_series_4h.diff(3)),
            }
            
            long_score  = fuzzy.compute_long_score(indicators)
            short_score = fuzzy.compute_short_score(indicators)
            
            # Fetch live threshold from Redis
            threshold = await self.state.get_float("settings:position_threshold") or 0.65
            action, conviction = fuzzy.should_trade(long_score, short_score, 'POSITION', threshold=threshold)
            
            # Store fuzzy scores for dashboard radar chart
            await self.state.set(f"fuzzy_scores:{symbol}", {
                "rsi": indicators['rsi'],
                "vwap": (df_4h['close'].iloc[-1] - indicators['vwap']) / indicators['vwap'] * 100,
                "vol": indicators['vol_ratio'],
                "adx": indicators['adx'],
                "long": long_score,
                "short": short_score
            })
            
            log.info(f"🧠 [POSITION FUZZY] {symbol} long={long_score:.3f} short={short_score:.3f} → {action} (thresh={threshold})")
            
            if action == 'BUY' and structure == 'BULL' and ml_dir == 'BUY':
                log.info(f"🏔️ [POSITION] Entry LONG {symbol} | Fuzzy:{conviction:.2f} | ML:{ml_conf:.2%}")
                await self._open_position(symbol, 'LONG', price, atr_4h, conviction)
            elif action == 'SELL' and structure == 'BEAR' and ml_dir == 'SELL':
                log.info(f"🏔️ [POSITION] Entry SHORT {symbol} | Fuzzy:{conviction:.2f} | ML:{ml_conf:.2%}")
                await self._open_position(symbol, 'SHORT', price, atr_4h, conviction)

    async def _open_position(self, symbol: str, side: str, price: float, atr: float, conviction: float):
        qty = (self.capital * 0.6) / price
        stop = price - 2.5 * atr if side == 'LONG' else price + 2.5 * atr
        tp1 = price + 3.0 * atr if side == 'LONG' else price - 3.0 * atr
        tp2 = price + 6.0 * atr if side == 'LONG' else price - 6.0 * atr
        
        pos = {
            'state': 'FULL',
            'side': side,
            'entry': price,
            'qty': qty,
            'stop': stop,
            'tp1': tp1,
            'tp2': tp2,
            'time': time.time(),
            'highest': price,
            'lowest': price,
            'strategy': 'POSITION'
        }
        await self.state.set(f"position:pos:{symbol}", pos)
        
        req = {'action': 'OPEN', 'side': side, 'qty': qty, 'price': price, 'stop': stop, 'tp': tp2, 'strategy': 'POSITION'}
        await self.state.set(f"order_request:{symbol}", req)

        # Record signal for dashboard
        signal = {
            'time': time.time(),
            'price': price,
            'type': 'LONG' if side == 'LONG' else 'SHORT',
            'action': 'OPEN',
            'strategy': 'POSITION'
        }
        await self.state.redis.lpush('signals:history', json.dumps(signal))
        await self.state.redis.ltrim('signals:history', 0, 99)

        # Telegram notification
        from core.telegram_notifier import TelegramNotifier
        await TelegramNotifier().trade_opened('POSITION', symbol, side, price, qty, stop, tp2, conviction)

        log.info(f"🏔️ [POSITION] OPEN {side} {symbol} at {price:.2f}")

    async def _close_partial(self, symbol: str, pos: dict, price: float, qty: float, reason: str):
        entry = pos['entry']
        side = pos['side']
        pnl_usd = (price - entry) * qty if side == 'LONG' else (entry - price) * qty

        await self.pnl.record_trade('POSITION', symbol, side, entry, price, qty, reason)
        
        # Duration
        duration_seconds = time.time() - pos.get('time', time.time())
        duration_str = f"{int(duration_seconds/3600)}h" if duration_seconds > 3600 else f"{int(duration_seconds/60)}m"

        # Telegram notification
        from core.telegram_notifier import TelegramNotifier
        await TelegramNotifier().trade_closed('POSITION', symbol, side, entry, price, qty, pnl_usd, f"PARTIAL_{reason}", duration_str)

        req = {'action': 'CLOSE', 'side': side, 'qty': qty, 'strategy': 'POSITION'}
        await self.state.set(f"order_request:{symbol}", req)

    async def _close_position(self, symbol: str, pos: dict, price: float, reason: str):
        entry = pos['entry']
        side = pos['side']
        qty = pos['qty']
        pnl_usd = (price - entry) * qty if side == 'LONG' else (entry - price) * qty

        await self.pnl.record_trade('POSITION', symbol, side, entry, price, qty, reason)
        
        # Duration
        duration_seconds = time.time() - pos.get('time', time.time())
        duration_str = f"{int(duration_seconds/3600)}h" if duration_seconds > 3600 else f"{int(duration_seconds/60)}m"

        # Telegram notification
        from core.telegram_notifier import TelegramNotifier
        await TelegramNotifier().trade_closed('POSITION', symbol, side, entry, price, qty, pnl_usd, reason, duration_str)

        await self.state.redis.delete(f"position:pos:{symbol}")
        
        req = {'action': 'CLOSE', 'side': side, 'qty': qty, 'strategy': 'POSITION'}
        await self.state.set(f"order_request:{symbol}", req)
