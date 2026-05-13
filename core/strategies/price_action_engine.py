"""
core/strategies/price_action_engine.py  — PHASE 9 REBUILD

Zone proximity fix:
  OLD: PROXIMITY_PCT = 0.005  (0.5% — kills BUY signals in trending markets)
  NEW: PROXIMITY_PCT = 0.025  (2.5%)

Entry confirmation fallback:
  If no zone is within 2.5%, the new entry_confirmed() method fires when
  price pulls back to EMA20 in an EMA20 > EMA50 (bull) or EMA20 < EMA50
  (bear) structure. This fires consistently during trends.
"""

import pandas as pd
import numpy as np
from typing import List, Tuple, Dict
import logging

log = logging.getLogger("PriceActionEngine")


class PriceActionZoneEngine:
    """
    Identifies high-probability support/resistance zones using:
    - Historical price reaction points (pivot clusters)
    - Fibonacci retracements
    - Role reversals (Support <-> Resistance)
    """

    def __init__(self):
        self.FIBONACCI_RATIOS = [0.236, 0.382, 0.618, 0.786, 1.0]
        self.ZONE_WIDTH_PCT   = 0.3   # 0.3% tolerance around fixed levels

    def find_major_zones(self, df: pd.DataFrame, window: int = 252) -> Dict[str, List[float]]:
        """Find major S/R zones over a lookback window."""
        if df is None or len(df) < 50:
            return {"resistance": [], "support": []}

        df = df.tail(window).copy()
        highs = df["high"].values
        lows  = df["low"].values

        resistance_candidates = []
        support_candidates    = []

        for i in range(2, len(df) - 2):
            if highs[i] > highs[i-1] and highs[i] > highs[i-2] and \
               highs[i] > highs[i+1] and highs[i] > highs[i+2]:
                resistance_candidates.append(highs[i])

            if lows[i] < lows[i-1] and lows[i] < lows[i-2] and \
               lows[i] < lows[i+1] and lows[i] < lows[i+2]:
                support_candidates.append(lows[i])

        resistance_candidates.append(df["high"].max())
        support_candidates.append(df["low"].min())

        return {
            "resistance": sorted(self._cluster_zones(resistance_candidates), reverse=True),
            "support":    sorted(self._cluster_zones(support_candidates)),
        }

    def calculate_fibonacci_levels(self, swing_low: float, swing_high: float) -> Dict[str, float]:
        if swing_high == swing_low:
            return {}
        diff   = swing_high - swing_low
        levels = {}
        for ratio in self.FIBONACCI_RATIOS:
            level = swing_high - (diff * ratio) if swing_high > swing_low \
                    else swing_low + (diff * ratio)
            levels[str(ratio)] = round(level, 8)
        return levels

    def _cluster_zones(self, levels: List[float], tolerance_pct: float = None) -> List[float]:
        if not levels:
            return []
        tol = tolerance_pct or self.ZONE_WIDTH_PCT
        sorted_levels   = sorted(levels)
        clusters        = []
        current_cluster = [sorted_levels[0]]

        for level in sorted_levels[1:]:
            if abs(level - current_cluster[-1]) / current_cluster[-1] <= tol / 100:
                current_cluster.append(level)
            else:
                clusters.append(float(np.mean(current_cluster)))
                current_cluster = [level]
        clusters.append(float(np.mean(current_cluster)))
        return clusters


class ZoneTradeFilter:
    """
    PHASE 9: Proximity raised from 0.5% → 2.5%.
    Adds entry_confirmed() pullback method as primary confirmation in trends.
    """

    # PHASE 9 FIX: was 0.005 (0.5%) — too tight to fire in trending markets
    PROXIMITY_PCT = 0.025  # 2.5%

    def __init__(self, engine: PriceActionZoneEngine):
        self.engine = engine

    def validate_entry(self, side: str, price: float,
                       zones: Dict, fibs: Dict) -> Tuple[bool, float]:
        """
        Structural confluence check.  Returns (is_valid, score).
        Checks zone proximity AND fib proximity at 2.5% tolerance.
        """
        score = 0.0
        relevant_zones = zones["support"] if side == "BUY" else zones["resistance"]

        for z in relevant_zones:
            if z > 0 and abs(price - z) / z <= self.PROXIMITY_PCT:
                score += 1.0
                break

        for ratio, f_val in fibs.items():
            if f_val > 0 and abs(price - f_val) / f_val <= self.PROXIMITY_PCT:
                mult   = 1.2 if ratio == "0.618" else 1.0
                score += 1.0 * mult
                break

        return score >= 1.0, score

    @staticmethod
    def entry_confirmed(price: float, ema20: float, ema50: float, side: str) -> bool:
        """
        PHASE 9 fallback confirmation: pullback to EMA20 in a trending structure.
        Used when zone proximity is not met but trend structure is clear.

          LONG : price <= EMA20 * 1.005  AND  EMA20 > EMA50  (bull pullback)
          SHORT: price >= EMA20 * 0.995  AND  EMA20 < EMA50  (bear rally)
        """
        if side == "BUY":
            return price <= ema20 * 1.005 and ema20 > ema50
        elif side == "SELL":
            return price >= ema20 * 0.995 and ema20 < ema50
        return False


# ── Module-level helpers (unchanged API) ────────────────────────────────────

def calculate_swing_points(df: pd.DataFrame, window: int = 30) -> Dict[str, float]:
    h_idx = df["high"].tail(window).idxmax()
    l_idx = df["low"].tail(window).idxmin()
    return {
        "high":      float(df["high"].loc[h_idx]),
        "low":       float(df["low"].loc[l_idx]),
        "high_time": h_idx,
        "low_time":  l_idx,
    }

def get_fib_retracements(low: float, high: float) -> Dict[str, float]:
    return PriceActionZoneEngine().calculate_fibonacci_levels(low, high)
