"""
core/position_manager.py
Async Position Manager — Phase 2 (Forced Decision Mode)

Acts on every BUY/SELL/NEUTRAL decision from the ensemble scorer
every 60 seconds. The bot must always be in a position or just exited one.
"""

import asyncio
import logging
from config import SYMBOLS
from core.state_manager import StateManager

log = logging.getLogger("PositionManager")


class PositionManager:
    def __init__(self, state: StateManager):
        self.state = state
        self.log = log

    async def run_loop(self, interval: int = 60):
        self.log.info("🚀 Position Manager Loop Started (interval=60s)")

        while True:
            for symbol in SYMBOLS:
                try:
                    ensemble = await self.state.get(f"ensemble:{symbol}")
                    if not ensemble:
                        continue

                    action = ensemble.get('action', 'NEUTRAL')
                    conviction = ensemble.get('conviction', 0.0)
                    price = await self.state.get_float(f"price:{symbol}")
                    position = await self.state.get_position(symbol)

                    self.log.info(
                        f"[DECISION] {symbol} → {action} "
                        f"conviction={conviction:.2f} "
                        f"price={price}"
                    )

                    # ── Currently in NO position ──
                    if not position or position.get('status') == 'CLOSED':
                        if action == "BUY":
                            await self._open_position(
                                symbol, "LONG", conviction, price)
                        elif action == "SELL":
                            await self._open_position(
                                symbol, "SHORT", conviction, price)
                        # NEUTRAL = stay out, do nothing

                    # ── Currently in a LONG position ──
                    elif position.get('side') == 'LONG':
                        if action == "SELL":
                            await self._close_position(
                                symbol, position, price, "SIGNAL_FLIP")
                            await self._open_position(
                                symbol, "SHORT", conviction, price)
                        elif action == "NEUTRAL":
                            await self._close_position(
                                symbol, position, price, "NEUTRAL_EXIT")
                        # BUY = hold current long

                    # ── Currently in a SHORT position ──
                    elif position.get('side') == 'SHORT':
                        if action == "BUY":
                            await self._close_position(
                                symbol, position, price, "SIGNAL_FLIP")
                            await self._open_position(
                                symbol, "LONG", conviction, price)
                        elif action == "NEUTRAL":
                            await self._close_position(
                                symbol, position, price, "NEUTRAL_EXIT")
                        # SELL = hold current short

                    # ── Update trailing stop on open positions ──
                    if position and position.get('status') == 'OPEN':
                        await self._update_trailing_stop(
                            symbol, position, price)

                except Exception as e:
                    self.log.error(f"PositionManager error {symbol}: {e}")

            await asyncio.sleep(interval)

    async def _open_position(self, symbol: str, side: str,
                             conviction: float, price: float):
        """Open a paper trade position in Redis."""
        atr = await self.state.get_float(f"atr:{symbol}") or price * 0.01
        stop = price - 1.5 * atr if side == "LONG" else price + 1.5 * atr
        tp1 = price + 3.0 * atr if side == "LONG" else price - 3.0 * atr
        qty = 10.0 / price  # $10 per trade in paper mode

        position = {
            "status": "OPEN",
            "side": side,
            "entry": price,
            "qty": qty,
            "stop": stop,
            "tp1": tp1,
            "open_time": asyncio.get_event_loop().time(),
            "conviction": conviction,
        }
        await self.state.set_position(symbol, position)

        # Also publish order_request for order engine compatibility
        req = {
            'action': 'OPEN',
            'side': side,
            'qty': float(qty),
            'price': float(price),
            'stop': float(stop),
            'tp': float(tp1),
        }
        await self.state.set(f"order_request:{symbol}", req)

        self.log.info(
            f"📝 PAPER TRADE OPEN: {side} {symbol} "
            f"qty={qty:.6f} entry={price:.2f} "
            f"stop={stop:.2f} tp1={tp1:.2f}"
        )

    async def _close_position(self, symbol: str, position: dict,
                              price: float, reason: str):
        """Close an open position and log the reason."""
        side = position.get('side', 'LONG')
        qty = position.get('qty', 0.0)
        entry = position.get('entry', price)

        # Calculate P&L
        if side == 'LONG':
            pnl = (price - entry) * qty
        else:
            pnl = (entry - price) * qty

        # Mark position as closed
        position['status'] = 'CLOSED'
        position['exit_price'] = price
        position['pnl'] = pnl
        position['close_reason'] = reason
        await self.state.set_position(symbol, position)

        # Publish close request for order engine
        req = {
            'action': 'CLOSE',
            'side': side,
            'qty': float(qty),
        }
        await self.state.set(f"order_request:{symbol}", req)

        self.log.info(
            f"📝 PAPER TRADE CLOSE: {side} {symbol} "
            f"entry={entry:.2f} exit={price:.2f} "
            f"pnl={pnl:.4f} reason={reason}"
        )

    async def _update_trailing_stop(self, symbol: str, pos: dict,
                                    price: float):
        """Update highest/lowest price and trail stop in Redis."""
        atr = await self.state.get_float(f"atr:{symbol}") or price * 0.01
        trail_dist = 1.5 * atr

        updated = False
        highest = pos.get('highest_price', pos.get('entry', price))
        lowest = pos.get('lowest_price', pos.get('entry', price))

        if pos.get('side') == 'LONG':
            if price > highest:
                pos['highest_price'] = price
                new_stop = price - trail_dist
                if new_stop > pos.get('stop', 0):
                    pos['stop'] = new_stop
                    updated = True
        elif pos.get('side') == 'SHORT':
            if price < lowest:
                pos['lowest_price'] = price
                new_stop = price + trail_dist
                if new_stop < pos.get('stop', float('inf')):
                    pos['stop'] = new_stop
                    updated = True

        if updated:
            await self.state.set_position(symbol, pos)
