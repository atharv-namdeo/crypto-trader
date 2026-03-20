"""
core/position_tracker.py
In-memory Position Manager — Phase 1

Tracks all open positions, updates trailing stops every cycle,
handles TP1 (50% at 2:1 RR), TP2 (remaining at 4:1 RR),
and position flip logic when ensemble score reverses.
"""

import time
import logging
from dataclasses import dataclass, field
from typing import Optional

log = logging.getLogger("PositionTracker")


@dataclass
class Position:
    symbol: str
    side: str                   # 'LONG' | 'SHORT'
    entry: float
    qty: float
    stop: float
    tp1: float
    tp2: float
    score_at_entry: float
    open_time: float = field(default_factory=time.time)
    tp1_hit: bool = False
    qty_remaining: float = 0.0  # set to qty on open
    highest_price: float = 0.0  # for trailing (LONG)
    lowest_price: float = 0.0   # for trailing (SHORT)
    tier: str = 'INTRADAY'

    def __post_init__(self):
        if self.qty_remaining == 0.0:
            self.qty_remaining = self.qty
        if self.highest_price == 0.0:
            self.highest_price = self.entry
        if self.lowest_price == 0.0:
            self.lowest_price = self.entry

    @property
    def unrealized_pnl_pct(self) -> float:
        if self.side == 'LONG':
            return (self._current_price - self.entry) / self.entry
        else:
            return (self.entry - self._current_price) / self.entry

    _current_price: float = 0.0


# ── Time stop limits per tier ──────────────────────────────────────────────
MAX_AGE_SECONDS = {
    'SCALP':    300,       # 5 minutes
    'INTRADAY': 28_800,    # 8 hours
    'SWING':    604_800,   # 7 days
}

# ── Trailing / TP config ───────────────────────────────────────────────────
STOP_ATR_MULTIPLE = 1.5
TP1_RR            = 2.0   # TP1 at 2:1 RR → close 50%
TP2_RR            = 4.0   # TP2 at 4:1 RR → close rest

# Score thresholds for position management
FLIP_THRESHOLD   = 0.45   # reverse direction when score crosses this
REDUCE_THRESHOLD = 0.15   # weaken → reduce 30%


class PositionTracker:
    """Thread-safe in-memory position tracker (one dict per symbol)."""

    def __init__(self):
        self._positions: dict[str, Optional[Position]] = {}  # symbol → Position or None

    # ── Public API ────────────────────────────────────────────────────────

    def open_position(
        self,
        symbol: str,
        side: str,
        entry: float,
        qty: float,
        atr: float,
        score: float,
        tier: str = 'INTRADAY',
    ) -> Position:
        stop_dist = STOP_ATR_MULTIPLE * atr
        tp1_dist  = stop_dist * TP1_RR
        tp2_dist  = stop_dist * TP2_RR

        if side == 'LONG':
            stop = entry - stop_dist
            tp1  = entry + tp1_dist
            tp2  = entry + tp2_dist
        else:
            stop = entry + stop_dist
            tp1  = entry - tp1_dist
            tp2  = entry - tp2_dist

        pos = Position(
            symbol=symbol, side=side, entry=entry, qty=qty,
            stop=stop, tp1=tp1, tp2=tp2, score_at_entry=score,
            tier=tier,
        )
        self._positions[symbol] = pos
        log.info(f"[{symbol}] OPEN {side} @ {entry:.4f} | "
                 f"SL={stop:.4f} TP1={tp1:.4f} TP2={tp2:.4f} qty={qty:.6f}")
        return pos

    def get_position(self, symbol: str) -> Optional[Position]:
        return self._positions.get(symbol)

    def has_position(self, symbol: str) -> bool:
        p = self._positions.get(symbol)
        return p is not None

    def close_position(self, symbol: str, price: float, reason: str = '') -> Optional[Position]:
        pos = self._positions.pop(symbol, None)
        if pos:
            pnl_pct = ((price - pos.entry) / pos.entry) * (1 if pos.side == 'LONG' else -1)
            log.info(f"[{symbol}] CLOSE {pos.side} @ {price:.4f} | "
                     f"PnL={pnl_pct:+.2%} | reason={reason}")
        return pos

    def update(self, symbol: str, price: float, atr: float, ensemble_score: float) -> dict:
        """
        Called every cycle. Updates trailing stop, checks TP/SL, manages flip/reduce.
        Returns action dict: {'action': 'HOLD'|'CLOSE'|'REDUCE'|'FLIP', 'reason': str}
        """
        pos = self._positions.get(symbol)
        if pos is None:
            return {'action': 'NONE'}

        pos._current_price = price

        # 1. Time stop
        age = time.time() - pos.open_time
        if age > MAX_AGE_SECONDS.get(pos.tier, 28_800):
            self.close_position(symbol, price, 'TIME_STOP')
            return {'action': 'CLOSE', 'reason': 'TIME_STOP'}

        # 2. Hard stop hit
        if self._stop_hit(pos, price):
            self.close_position(symbol, price, 'STOP_LOSS')
            return {'action': 'CLOSE', 'reason': 'STOP_LOSS'}

        # 3. TP1 (50% exit, move stop to breakeven)
        if not pos.tp1_hit and self._tp1_hit(pos, price):
            pos.tp1_hit = True
            pos.qty_remaining *= 0.5
            pos.stop = pos.entry  # breakeven stop
            log.info(f"[{symbol}] TP1 HIT @ {price:.4f} | 50% closed | stop → breakeven")
            return {'action': 'REDUCE', 'reason': 'TP1_HIT', 'qty': pos.qty * 0.5}

        # 4. TP2 (full close)
        if pos.tp1_hit and self._tp2_hit(pos, price):
            self.close_position(symbol, price, 'TP2_HIT')
            return {'action': 'CLOSE', 'reason': 'TP2_HIT'}

        # 5. Signal FLIP — score crosses strongly in opposite direction
        pos_sign = 1 if pos.side == 'LONG' else -1
        aligned_score = ensemble_score * pos_sign
        if aligned_score < -FLIP_THRESHOLD:
            self.close_position(symbol, price, 'SIGNAL_FLIP')
            return {'action': 'FLIP', 'reason': 'SIGNAL_FLIP',
                    'new_side': 'SHORT' if pos.side == 'LONG' else 'LONG'}

        # 6. Signal weakening → reduce 30%
        if aligned_score < REDUCE_THRESHOLD and not pos.tp1_hit:
            reduce_qty = pos.qty_remaining * 0.30
            pos.qty_remaining -= reduce_qty
            if pos.qty_remaining < pos.qty * 0.05:
                self.close_position(symbol, price, 'SIGNAL_WEAK_FULL')
                return {'action': 'CLOSE', 'reason': 'SIGNAL_WEAK'}
            log.info(f"[{symbol}] REDUCE 30% | score={ensemble_score:.3f}")
            return {'action': 'REDUCE', 'reason': 'SIGNAL_WEAK', 'qty': reduce_qty}

        # 7. Update trailing stop (only moves in profitable direction)
        self._update_trailing(pos, price, atr)

        return {'action': 'HOLD'}

    def get_all_positions(self) -> dict:
        return dict(self._positions)

    def total_heat(self, portfolio_value: float, capital: float) -> float:
        """Returns approximate total portfolio risk as fraction."""
        heat = 0.0
        for pos in self._positions.values():
            if pos:
                stop_dist = abs(pos.entry - pos.stop) / pos.entry
                heat += stop_dist * (pos.qty_remaining * pos.entry / capital)
        return heat

    # ── Private helpers ───────────────────────────────────────────────────

    def _stop_hit(self, pos: Position, price: float) -> bool:
        return (pos.side == 'LONG' and price <= pos.stop) or \
               (pos.side == 'SHORT' and price >= pos.stop)

    def _tp1_hit(self, pos: Position, price: float) -> bool:
        return (pos.side == 'LONG' and price >= pos.tp1) or \
               (pos.side == 'SHORT' and price <= pos.tp1)

    def _tp2_hit(self, pos: Position, price: float) -> bool:
        return (pos.side == 'LONG' and price >= pos.tp2) or \
               (pos.side == 'SHORT' and price <= pos.tp2)

    def _update_trailing(self, pos: Position, price: float, atr: float):
        trail_dist = STOP_ATR_MULTIPLE * atr
        if pos.side == 'LONG':
            if price > pos.highest_price:
                pos.highest_price = price
                new_stop = price - trail_dist
                if new_stop > pos.stop:  # only move UP
                    pos.stop = new_stop
        elif pos.side == 'SHORT':
            if price < pos.lowest_price:
                pos.lowest_price = price
                new_stop = price + trail_dist
                if new_stop < pos.stop:  # only move DOWN
                    pos.stop = new_stop
