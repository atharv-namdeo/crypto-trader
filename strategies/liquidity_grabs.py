"""LIQUIDITY_GRAB — Smart money grab detection at equal highs/lows."""
import numpy as np
from strategies.base import BaseStrategy

class LiquidityGrabs(BaseStrategy):
    NAME = "LIQUIDITY_GRAB"

    def calculate_signal(self, ohlcv: dict) -> float:
        df = ohlcv.get('1h')
        if df is None or len(df) < 30:
            return 0.0

        recent = df.tail(30)
        price = df['close'].iloc[-1]
        high = df['high'].iloc[-1]
        low = df['low'].iloc[-1]
        atr = self._atr(df, 14).iloc[-1]

        max_high = recent['high'].max()
        min_low = recent['low'].min()

        score = 0.0
        # Bullish grab: wick below equal lows then close above
        if low < min_low and price > min_low:
            grab_size = (min_low - low) / (atr + 1e-9)
            score = min(0.3 + grab_size * 0.4, 0.9)
        # Bearish grab: wick above equal highs then close below
        elif high > max_high and price < max_high:
            grab_size = (high - max_high) / (atr + 1e-9)
            score = -min(0.3 + grab_size * 0.4, 0.9)
        else:
            # Weak signal: proximity to liquidity pools
            mid = (max_high + min_low) / 2
            rng = max_high - min_low + 1e-9
            score = (price - mid) / rng * 0.15

        return self._clip(score)
