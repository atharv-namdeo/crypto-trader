"""BREAKOUT — Volatility breakout with volume surge confirmation."""
import numpy as np
from strategies.base import BaseStrategy

class VolatilityBreakout(BaseStrategy):
    NAME = "BREAKOUT"

    def calculate_signal(self, ohlcv: dict) -> float:
        df = ohlcv.get('1h')
        if df is None or len(df) < 30:
            return 0.0

        high_20 = df['high'].rolling(20).max().iloc[-2]
        low_20 = df['low'].rolling(20).min().iloc[-2]
        current = df['close'].iloc[-1]
        vol_sma = df['volume'].rolling(20).mean()
        vol_surge = df['volume'].iloc[-1] / (vol_sma.iloc[-1] + 1e-9)

        if current > high_20 and vol_surge > 1.5:
            score = min(vol_surge / 3.0, 1.0)
        elif current < low_20 and vol_surge > 1.5:
            score = -min(vol_surge / 3.0, 1.0)
        else:
            range_size = high_20 - low_20
            mid = (high_20 + low_20) / 2
            score = (current - mid) / (range_size / 2 + 1e-9)
            score = float(np.clip(score * 0.3, -0.3, 0.3))

        return self._clip(score)
