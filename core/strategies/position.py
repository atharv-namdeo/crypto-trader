import asyncio
import logging
import time
from core.state_manager import StateManager
from core.pnl_tracker import PnLTracker
from strategies.utils import compute_rsi, compute_adx, compute_atr

log = logging.getLogger("PositionTrader")

class PositionStrategy:
    def __init__(self, state: StateManager, pnl_tracker: PnLTracker, capital: float = 400.0):
        self.state = state
        self.pnl = pnl_tracker
        self.capital = capital
        self.symbols = ["BTC/USDT"] # Single specific concentration
        self.running = False

    async def run_loop(self):
        self.running = True
        log.info(f"🏔️ Start POSITION Loop (Cap: ${self.capital})")
        while self.running:
            try:
                for symbol in self.symbols:
                    await self._process(symbol)
            except asyncio.CancelledError:
                break
            except Exception as e:
                log.error(f"PositionTrader error: {e}")
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
        
        adx_4h = compute_adx(df_4h, 14).iloc[-1]
        strong_trend = adx_4h > 25
        
        ema20_1d = df_1d['close'].ewm(span=20).mean().iloc[-1]
        ema50_1d = df_1d['close'].ewm(span=50).mean().iloc[-1]
        daily_bull = ema20_1d > ema50_1d
        
        vol_increasing = df_4h['volume'].iloc[-3:].mean() > df_4h['volume'].iloc[-10:-3].mean()
        
        structure = 'NEUTRAL'
        if daily_bull and strong_trend and vol_increasing:
            structure = 'BULL'
        elif not daily_bull and strong_trend and vol_increasing:
            structure = 'BEAR'
            
        atr_4h = compute_atr(df_4h, 14).iloc[-1]
        
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

            rsi_4h = compute_rsi(df_4h['close'], 14)
            dip = rsi_4h.iloc[-1] < 45 and rsi_4h.iloc[-2] < 45
            ema20_4h = df_4h['close'].ewm(span=20).mean().iloc[-1]
            near_support = price < ema20_4h * 1.01
            
            bounce = rsi_4h.iloc[-1] > 60 and rsi_4h.iloc[-2] > 60
            near_resistance = price > ema20_4h * 0.99
            
            if structure == 'BULL' and dip and near_support:
                await self._open_position(symbol, 'LONG', price, atr_4h)
            elif structure == 'BEAR' and bounce and near_resistance:
                await self._open_position(symbol, 'SHORT', price, atr_4h)

    async def _open_position(self, symbol: str, side: str, price: float, atr: float):
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
            'lowest': price
        }
        await self.state.set(f"position:pos:{symbol}", pos)
        
        req = {'action': 'OPEN', 'side': side, 'qty': qty, 'price': price, 'stop': stop, 'tp': tp2}
        await self.state.set(f"order_request:{symbol}", req)
        log.info(f"🏔️ [POSITION] OPEN {side} {symbol} at {price:.2f}")

    async def _close_partial(self, symbol: str, pos: dict, price: float, qty: float, reason: str):
        await self.pnl.record_trade('POSITION', symbol, pos['side'], pos['entry'], price, qty, reason)
        # Send physical close for partial size to Binance
        req = {'action': 'CLOSE', 'side': pos['side'], 'qty': qty}
        await self.state.set(f"order_request:{symbol}", req)

    async def _close_position(self, symbol: str, pos: dict, price: float, reason: str):
        await self.pnl.record_trade('POSITION', symbol, pos['side'], pos['entry'], price, pos['qty'], reason)
        await self.state.redis.delete(f"position:pos:{symbol}")
        
        req = {'action': 'CLOSE', 'side': pos['side'], 'qty': pos['qty']}
        await self.state.set(f"order_request:{symbol}", req)
