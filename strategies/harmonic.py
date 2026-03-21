"""HARMONIC — Harmonic pattern detection via swing ratio analysis."""
import numpy as np
from strategies.base import BaseStrategy

class HarmonicPatterns(BaseStrategy):
    NAME = "HARMONIC"

    def calculate_signal(self, ohlcv: dict) -> float:
        df = ohlcv.get('1h')
        if df is None or len(df) < 60:
            return 0.0
        close = df['close']

        # Detect swing points
        high_roll = df['high'].rolling(10, center=True).max()
        low_roll = df['low'].rolling(10, center=True).min()

        swing_highs = df[df['high'] == high_roll].tail(3)
        swing_lows = df[df['low'] == low_roll].tail(3)

        if len(swing_highs) < 2 or len(swing_lows) < 2:
            # Fallback: simple RSI-based signal
            rsi = self._rsi(close, 14).iloc[-1]
            return self._clip(-(rsi - 50) / 80)

        price = close.iloc[-1]

        # Check for bullish Gartley-like (AB retraces ~0.618 of XA)
        x = swing_lows['low'].iloc[-2]
        a = swing_highs['high'].iloc[-2]
        b = swing_lows['low'].iloc[-1]
        xa = a - x
        if abs(xa) < 1e-9:
            return 0.0
        ab_ratio = (a - b) / xa

        if 0.5 <= ab_ratio <= 0.8 and price <= b * 1.01:
            score = 0.5 * (1 - abs(ab_ratio - 0.618) / 0.2)
            return self._clip(score)

        # Bearish pattern
        x2 = swing_highs['high'].iloc[-2]
        a2 = swing_lows['low'].iloc[-2]
        b2 = swing_highs['high'].iloc[-1]
        xa2 = x2 - a2
        if abs(xa2) < 1e-9:
            return 0.0
        ab_ratio2 = (b2 - a2) / xa2

        if 0.5 <= ab_ratio2 <= 0.8 and price >= b2 * 0.99:
            score = -0.5 * (1 - abs(ab_ratio2 - 0.618) / 0.2)
            return self._clip(score)

        # No pattern, use basic price-vs-swing midpoint
        mid = (swing_highs['high'].max() + swing_lows['low'].min()) / 2
        atr = self._atr(df, 14).iloc[-1]
        return self._clip((price - mid) / (atr * 5 + 1e-9) * 0.2)
