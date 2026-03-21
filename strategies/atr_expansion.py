"""ATR_EXPANSION — Volatility expansion with directional bias."""
import numpy as np
from strategies.base import BaseStrategy

class ATRExpansion(BaseStrategy):
    NAME = "ATR_EXPANSION"

    def calculate_signal(self, ohlcv: dict) -> float:
        df = ohlcv.get('1h')
        if df is None or len(df) < 30:
            return 0.0
        close = df['close']

        atr = self._atr(df, 14)
        atr_sma = atr.rolling(20).mean()
        current_atr = atr.iloc[-1]
        avg_atr = atr_sma.iloc[-1]

        # Vol expansion ratio
        vol_ratio = current_atr / (avg_atr + 1e-9)

        # Direction from EMA
        ema20 = close.ewm(span=20).mean().iloc[-1]
        direction = 1.0 if close.iloc[-1] > ema20 else -1.0

        # Score: higher vol expansion = stronger signal in trend direction
        if vol_ratio > 1.5:
            score = direction * min(vol_ratio / 3.0, 0.8)
        else:
            score = direction * 0.1  # weak directional bias

        return self._clip(score)
