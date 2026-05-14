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
    COMPRESSION   = "COMPRESSION"
    EXPLOSION     = "EXPLOSION"
    TRENDING_BULL = "TRENDING_BULL"
    TRENDING_BEAR = "TRENDING_BEAR"
    RANGING_BULL  = "RANGING_BULL"
    RANGING_BEAR  = "RANGING_BEAR"
    VOLATILE_BULL = "VOLATILE_BULL"
    VOLATILE_BEAR = "VOLATILE_BEAR"
    NEUTRAL       = "NEUTRAL"
    UNKNOWN       = "UNKNOWN"

class AdvancedRegimeDetector:
    """
    PHASE 11 — 8-state high-resolution regime classifier.
    Detects specific market archetypes (Compression, Explosion, Trending, Ranging).
    """

    def __init__(self):
        self.lookback = 200

    def classify_market(self, df: pd.DataFrame) -> MarketPhase:
        if df is None or len(df) < 50:
            return MarketPhase.UNKNOWN

        c = df["close"]
        h = df["high"]
        l = df["low"]
        v = df["volume"]
        
        # 1. Technical Baseline
        ema200 = c.ewm(span=200).mean().iloc[-1]
        price = c.iloc[-1]
        
        # 2. Volatility (ATR-based)
        from core.utils import compute_atr
        atr = compute_atr(df, 14)
        volatility = (atr.iloc[-1] / price) * 100
        
        # 3. Momentum (Slope of EMA20)
        ema20 = c.ewm(span=20).mean()
        slope = (ema20.iloc[-1] - ema20.iloc[-5]) / ema20.iloc[-5] * 100
        
        # 4. Volume Pressure
        v_sma = v.rolling(20).mean()
        v_ratio = v.iloc[-1] / (v_sma.iloc[-1] + 1e-9)

        # --- CLASSIFICATION LOGIC ---
        
        # A. Explosion (High Volume + High Momentum)
        if v_ratio > 2.0 and abs(slope) > 0.5:
            return MarketPhase.EXPLOSION
            
        # B. Compression (Low Volatility + Low Volume)
        if volatility < 0.5 and v_ratio < 0.8:
            return MarketPhase.COMPRESSION
            
        # C. Trending
        if abs(slope) > 0.3:
            if slope > 0: return MarketPhase.TRENDING_BULL
            else: return MarketPhase.TRENDING_BEAR
            
        # D. Volatile (High Volatility, low trend)
        if volatility > 2.0:
            if price > ema200: return MarketPhase.VOLATILE_BULL
            else: return MarketPhase.VOLATILE_BEAR
            
        # E. Ranging (Default)
        if price > ema200: return MarketPhase.RANGING_BULL
        else: return MarketPhase.RANGING_BEAR

    def get_risk_multiplier(self, phase: MarketPhase) -> float:
        return {
            MarketPhase.EXPLOSION:     1.5, # Aggressive
            MarketPhase.COMPRESSION:   0.5, # Small size for breakout fishing
            MarketPhase.TRENDING_BULL: 1.0,
            MarketPhase.TRENDING_BEAR: 1.0,
            MarketPhase.VOLATILE_BULL: 0.7, # Lower size due to noise
            MarketPhase.VOLATILE_BEAR: 0.7,
            MarketPhase.RANGING_BULL:  0.8,
            MarketPhase.RANGING_BEAR:  0.8,
        }.get(phase, 0.0)

    def is_trade_allowed(self, phase: MarketPhase, side: str) -> bool:
        """
        New granular gating logic.
        """
        # Explosion: Both sides allowed if momentum is massive
        if phase == MarketPhase.EXPLOSION: return True
        
        # Bull regimes: Mostly Longs, but allow shorts in Volatile/Ranging if signal is strong
        if phase in (MarketPhase.TRENDING_BULL, MarketPhase.VOLATILE_BULL, MarketPhase.RANGING_BULL):
            if side == "BUY": return True
            return phase != MarketPhase.TRENDING_BULL # No counter-trend shorts in strong uptrend
            
        # Bear regimes: Mostly Shorts
        if phase in (MarketPhase.TRENDING_BEAR, MarketPhase.VOLATILE_BEAR, MarketPhase.RANGING_BEAR):
            if side == "SELL": return True
            return phase != MarketPhase.TRENDING_BEAR
            
        return phase == MarketPhase.COMPRESSION # Allow both in compression

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
