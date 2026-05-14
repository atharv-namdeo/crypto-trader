"""
core/strategies/regime_classifier.py  — PHASE 9 REBUILD

Replaced 10-phase market cycle with a 3-state EMA-200 classifier.
Simple, robust, hard to mislabel. Prevents fighting the macro trend.

OLD: 10 phases (EARLY_BULL_BREAKOUT, MATURE_BULL_EXTENSION, etc.)
NEW: 3 states  (BULL, BEAR, NEUTRAL)

Rule:
  close >  EMA200 * 1.02  →  BULL   (longs only)
  close <  EMA200 * 0.98  →  BEAR   (shorts only)
  otherwise               →  NEUTRAL (no new trades)

EMA200 is computed on the 1h timeframe (last 200 closes).
"""

import pandas as pd
import numpy as np
from enum import Enum
from typing import Dict, Any

# ── Keep MarketPhase enum for import compatibility with other modules ──────────
class MarketPhase(Enum):
    BULL    = "BULL"     # price > 2% above EMA200 → longs only
    BEAR    = "BEAR"     # price > 2% below EMA200 → shorts only
    NEUTRAL = "NEUTRAL"  # within band            → no new trades
    UNKNOWN = "UNKNOWN"  # insufficient data

    # Legacy aliases kept so old code doesn't crash on .value comparisons
    EARLY_BULL_BREAKOUT   = "BULL"
    MATURE_BULL_EXTENSION = "BULL"
    BULL_CORRECTION       = "NEUTRAL"
    ACCUMULATION          = "NEUTRAL"
    DISTRIBUTION          = "NEUTRAL"
    EARLY_BEAR_BREAKDOWN  = "BEAR"
    MATURE_BEAR_DECLINE   = "BEAR"
    BEAR_BOUNCE           = "NEUTRAL"
    CONSOLIDATION_NARROW  = "NEUTRAL"
    CONSOLIDATION_WIDE    = "NEUTRAL"


class AdvancedRegimeDetector:
    """
    PHASE 9 — 3-state macro regime classifier.
    Uses EMA200 on the 1h timeframe.  Simple, robust, hard to mislabel.
    """

    # Deviation thresholds
    BULL_THRESHOLD    = 0.03   # +3% above EMA200 → BULL
    BEAR_THRESHOLD    = -0.03  # -3% below EMA200 → BEAR

    def __init__(self):
        self.lookback = 200   # EMA period

    # ── Public API (same signature as Phase 8) ─────────────────────────────

    def classify_market(self, df: pd.DataFrame) -> MarketPhase:
        """
        Classify market as BULL / BEAR / NEUTRAL using EMA200 deviation.
        Accepts any OHLCV DataFrame with a 'close' column.
        """
        if df is None or len(df) < 50:
            return MarketPhase.UNKNOWN

        closes   = df["close"].values
        ema200   = self._ema(closes, self.lookback)
        price    = float(closes[-1])
        deviation = (price - ema200) / ema200

        if deviation > self.BULL_THRESHOLD:
            return MarketPhase.BULL
        elif deviation < self.BEAR_THRESHOLD:
            return MarketPhase.BEAR
        else:
            return MarketPhase.NEUTRAL

    def get_risk_multiplier(self, phase: MarketPhase) -> float:
        """
        Size multiplier by regime.
        BULL/BEAR: 1.0 (normal size), NEUTRAL: 0.0 (no new trades).
        """
        return {
            MarketPhase.BULL:    1.0,
            MarketPhase.BEAR:    1.0,
            MarketPhase.NEUTRAL: 0.0,
            MarketPhase.UNKNOWN: 0.0,
        }.get(phase, 0.0)

    def is_trade_allowed(self, phase: MarketPhase, side: str) -> bool:
        """
        Hard gate: returns True only when side aligns with macro regime.
          BULL   → only BUY allowed
          BEAR   → only SELL allowed
          NEUTRAL / UNKNOWN → nothing allowed
        """
        if phase == MarketPhase.BULL and side == "BUY":
            return True
        if phase == MarketPhase.BEAR and side == "SELL":
            return True
        return False

    # ── Macro conflict check (used by order engine) ───────────────────────

    @staticmethod
    def macro_conflict_check(signal_side: str,
                             btc_close: float,
                             btc_ema200: float) -> tuple[bool, str]:
        """
        Final gate before order submission.
        Refuses trades that fight the BTC macro trend by more than 5%.
        Returns (allowed: bool, reason: str).
        """
        if btc_ema200 <= 0:
            return True, "OK (no EMA200 data)"

        deviation = (btc_close - btc_ema200) / btc_ema200

        if signal_side == "SHORT" and deviation > 0.05:
            return False, f"BLOCKED: shorting while BTC {deviation*100:.1f}%+ above EMA200"
        if signal_side == "LONG" and deviation < -0.05:
            return False, f"BLOCKED: longing while BTC {abs(deviation)*100:.1f}%+ below EMA200"
        return True, "OK"

    # ── Helpers ───────────────────────────────────────────────────────────

    @staticmethod
    def _ema(prices: np.ndarray, span: int) -> float:
        """Compute EMA and return last value."""
        s = pd.Series(prices, dtype=float)
        return float(s.ewm(span=span, adjust=False).mean().iloc[-1])

    def compute_ema200(self, df: pd.DataFrame) -> float:
        """Compute and return the current EMA200 close value."""
        if df is None or len(df) < 10:
            return 0.0
        return self._ema(df["close"].values, self.lookback)
