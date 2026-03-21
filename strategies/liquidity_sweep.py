"""LIQUIDITY_SWEEP — Detects sweeps of swing highs/lows followed by reversal candles."""
import numpy as np
from strategies.base import BaseStrategy

class LiquiditySweep(BaseStrategy):
    NAME = "LIQUIDITY_SWEEP"

    def calculate_signal(self, ohlcv: dict) -> float:
        df = ohlcv.get('1h')
        if df is None or len(df) < 30:
            return 0.0

        swing_high = df['high'].shift(1).rolling(20).max().iloc[-1]
        swing_low = df['low'].shift(1).rolling(20).min().iloc[-1]
        price = df['close'].iloc[-1]
        low = df['low'].iloc[-1]
        high = df['high'].iloc[-1]
        atr = self._atr(df, 14).iloc[-1]

        score = 0.0
        # Bullish sweep: wick below swing low but close above
        if low < swing_low and price > swing_low:
            sweep_depth = (swing_low - low) / (atr + 1e-9)
            score = min(0.3 + sweep_depth * 0.3, 0.9)
        # Bearish sweep: wick above swing high but close below
        elif high > swing_high and price < swing_high:
            sweep_depth = (high - swing_high) / (atr + 1e-9)
            score = -min(0.3 + sweep_depth * 0.3, 0.9)
        else:
            # Proximity to swing levels as weak signal
            mid = (swing_high + swing_low) / 2
            rng = swing_high - swing_low + 1e-9
            score = (price - mid) / rng * 0.15

        return self._clip(score)
