"""SUPERTREND — ATR-based trend bands direction and strength."""
import numpy as np
from strategies.base import BaseStrategy

class SupertrendStrategy(BaseStrategy):
    NAME = "SUPERTREND"

    def calculate_signal(self, ohlcv: dict) -> float:
        df = ohlcv.get('1h')
        if df is None or len(df) < 30:
            return 0.0
        close = df['close']

        atr = self._atr(df, 10)
        hl2 = (df['high'] + df['low']) / 2
        upper = hl2 + 3 * atr
        lower = hl2 - 3 * atr

        price = close.iloc[-1]
        upper_val = upper.iloc[-1]
        lower_val = lower.iloc[-1]
        mid = (upper_val + lower_val) / 2

        # Position relative to supertrend bands
        if price > upper_val:
            # Strong bullish: above upper band
            dist = (price - upper_val) / (atr.iloc[-1] + 1e-9)
            score = 0.4 + min(dist * 0.2, 0.4)
        elif price < lower_val:
            # Strong bearish: below lower band
            dist = (lower_val - price) / (atr.iloc[-1] + 1e-9)
            score = -(0.4 + min(dist * 0.2, 0.4))
        else:
            # Within bands: directional based on position
            score = (price - mid) / (upper_val - lower_val + 1e-9) * 0.5

        return self._clip(score)
