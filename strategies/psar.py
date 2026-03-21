"""PSAR — Parabolic SAR trend direction and distance."""
import numpy as np
from strategies.base import BaseStrategy

class ParabolicSAR(BaseStrategy):
    NAME = "PSAR"

    def calculate_signal(self, ohlcv: dict) -> float:
        df = ohlcv.get('1h')
        if df is None or len(df) < 30:
            return 0.0
        close = df['close']

        # Simple PSAR approximation using ATR-based trailing stop
        atr = self._atr(df, 14)
        ema = close.ewm(span=14).mean()
        atr_val = atr.iloc[-1]
        price = close.iloc[-1]
        ema_val = ema.iloc[-1]

        # If price > EMA → uptrend (SAR below), else downtrend
        if price > ema_val:
            sar = ema_val - 2 * atr_val
            dist = (price - sar) / (atr_val + 1e-9)
            score = min(dist * 0.15, 0.8)
        else:
            sar = ema_val + 2 * atr_val
            dist = (sar - price) / (atr_val + 1e-9)
            score = -min(dist * 0.15, 0.8)

        return self._clip(score)
