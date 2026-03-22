import asyncio
import logging
import time
from core.state_manager import StateManager
from core.pnl_tracker import PnLTracker
from strategies.utils import compute_rsi, compute_vwap, compute_atr

log = logging.getLogger("Scalper")

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
                for symbol in self.symbols:
                    await self._process(symbol)
            except asyncio.CancelledError:
                break
            except Exception as e:
                log.error(f"Scalper error: {e}")
            await asyncio.sleep(30)

    async def _process(self, symbol: str):
        df_1m = await self.state.get_df(f"ohlcv:1m:{symbol}", n=100)
        price = await self.state.get_float(f"price:{symbol}")
        if df_1m is None or len(df_1m) < 20 or not price:
            return

        pos = await self.state.get(f"scalper:pos:{symbol}")
        
        # Compute indicators
        rsi_1m = compute_rsi(df_1m['close'], 7).iloc[-1]
        vwap = compute_vwap(df_1m).iloc[-1]
        vol_sma = df_1m['volume'].rolling(10).mean().iloc[-1]
        vol_ratio = df_1m['volume'].iloc[-1] / (vol_sma + 1e-9)
        atr_1m = compute_atr(df_1m, 14).iloc[-1]
        
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

            if rsi_1m < 35 and price < vwap and vol_ratio > 1.3:
                await self._open_position(symbol, 'LONG', price)
            elif rsi_1m > 65 and price > vwap and vol_ratio > 1.3:
                await self._open_position(symbol, 'SHORT', price)

    async def _open_position(self, symbol: str, side: str, price: float):
        qty = (self.capital * 0.5) / price
        pos = {
            'side': side,
            'entry': price,
            'qty': qty,
            'time': time.time()
        }
        await self.state.set(f"scalper:pos:{symbol}", pos)
        
        # Send physical order request to Binance 
        req = {'action': 'OPEN', 'side': side, 'qty': qty, 'price': price, 'stop': 0, 'tp': 0}
        await self.state.set(f"order_request:{symbol}", req)
        
        log.info(f"⚡ [SCALPER] OPEN {side} {symbol} at {price:.2f}")

    async def _close_position(self, symbol: str, pos: dict, price: float, reason: str):
        # Calculate PNL and log
        await self.pnl.record_trade('SCALPER', symbol, pos['side'], pos['entry'], price, pos['qty'], reason)
        
        # Clear local state
        await self.state.redis.delete(f"scalper:pos:{symbol}")
        
        # Send physical close to Binance
        req = {'action': 'CLOSE', 'side': pos['side'], 'qty': pos['qty']}
        await self.state.set(f"order_request:{symbol}", req)
