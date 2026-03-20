"""
core/position_manager.py
Async Position Manager — Phase 4
"""

import time
import json
import asyncio
import logging
from config import SYMBOLS, CAPITAL
from core.state_manager import StateManager

log = logging.getLogger("PositionManager")

class PositionManager:
    def __init__(self, state: StateManager):
        self.state = state
        self.running = False
        
    async def run_loop(self, interval: int = 5):
        self.running = True
        log.info("🚀 Position Manager Loop Started")
        
        while self.running:
            try:
                for symbol in SYMBOLS:
                    await self._process_symbol(symbol)
            except asyncio.CancelledError:
                break
            except Exception as e:
                log.error(f"PositionManager loop error: {e}")
                
            await asyncio.sleep(interval)

    async def _process_symbol(self, symbol: str):
        # 1. Check current open position in Redis
        pos = await self.state.get_position(symbol)
        
        # 2. Check current ensemble score
        ensemble = await self.state.get(f"ensemble:{symbol}")
        score = ensemble.get('final_score', 0.0) if ensemble else 0.0
        
        price = await self.state.get_float(f"price:{symbol}")
        f = await self.state.get(f"features:{symbol}")
        atr = f.get('atr_14_1h', price * 0.01) if (f and price) else 0.0
        
        if not price or not atr:
            return

        # 3. Handle NO OPEN POSITION logic
        if not pos:
            # Task 3: If no open position and abs(score) > 0.25 → call _open_position
            if abs(score) > 0.25:
                side = 'LONG' if score > 0 else 'SHORT'
                await self._open_position(symbol, side, price, atr)
            return

        # 4. We HAVE an open position.
        # Check Flip Cooldown (Task 6)
        last_flip = await self.state.get_float(f"last_flip_time:{symbol}")
        can_flip = (time.time() - last_flip) >= 300

        # Flip logic for LONG
        if pos['side'] == 'LONG':
            if score < -0.45 and can_flip:
                log.info(f"🔄 FLIP {symbol} LONG to SHORT (Score: {score:.2f})")
                await self._close_position(symbol, pos['qty'])
                await self.state.set(f"last_flip_time:{symbol}", time.time())
                await self._open_position(symbol, 'SHORT', price, atr)
                return
            
        # Flip logic for SHORT
        elif pos['side'] == 'SHORT':
            if score > 0.45 and can_flip:
                log.info(f"🔄 FLIP {symbol} SHORT to LONG (Score: {score:.2f})")
                await self._close_position(symbol, pos['qty'])
                await self.state.set(f"last_flip_time:{symbol}", time.time())
                await self._open_position(symbol, 'LONG', price, atr)
                return

        # 5. Trailing Stops and Partial TPs
        await self._update_trailing_stop(symbol, pos, price, atr)
        await self._check_partial_tp(symbol, pos, price)

    async def _open_position(self, symbol: str, side: str, price: float, atr: float):
        """Publish order_request to Redis for the Order Engine."""
        # Simple sizing: risk 1% of max portfolio
        max_port = 500  # Will be controlled by risk guardian
        qty = (max_port * 0.01) / atr  # rough position size based on volatility
        
        stop_dist = 1.5 * atr
        stop = price - stop_dist if side == 'LONG' else price + stop_dist
        tp   = price + stop_dist * 3.0 if side == 'LONG' else price - stop_dist * 3.0
        
        req = {
            'action': 'OPEN',
            'side': side,
            'qty': float(qty),
            'price': float(price),
            'stop': float(stop),
            'tp': float(tp)
        }
        await self.state.set(f"order_request:{symbol}", req)
        log.info(f"📨 Published OPEN order_request for {symbol}: {req}")

    async def _close_position(self, symbol: str, qty: float):
        """Publish close request."""
        pos = await self.state.get_position(symbol)
        side = pos['side'] if pos else 'LONG'
        req = {
            'action': 'CLOSE',
            'side': side,
            'qty': float(qty)
        }
        await self.state.set(f"order_request:{symbol}", req)
        log.info(f"📨 Published CLOSE order_request for {symbol}")

    async def _update_trailing_stop(self, symbol: str, pos: dict, price: float, atr: float):
        """Update highest/lowest price and trail stop in Redis."""
        trail_dist = 1.5 * atr
        
        updated = False
        highest = pos.get('highest_price', pos['entry'])
        lowest = pos.get('lowest_price', pos['entry'])
        
        if pos['side'] == 'LONG':
            if price > highest:
                pos['highest_price'] = price
                new_stop = price - trail_dist
                if new_stop > pos['stop']:
                    pos['stop'] = new_stop
                    updated = True
        elif pos['side'] == 'SHORT':
            if price < lowest:
                pos['lowest_price'] = price
                new_stop = price + trail_dist
                if new_stop < pos['stop']:
                    pos['stop'] = new_stop
                    updated = True
                    
        if updated:
            await self.state.set_position(symbol, pos)

    async def _check_partial_tp(self, symbol: str, pos: dict, price: float):
        """Placeholder for 50% scale out."""
        # The true TP is handled by TAKE_PROFIT_MARKET on Binance
        # This function could manage multi-tier TPs if required.
        pass
