"""MEAN_REVERSION — Bollinger Band position + RSI as mean-reversion signal."""
import numpy as np
from strategies.base import BaseStrategy

class MeanReversion(BaseStrategy):
    NAME = "MEAN_REVERSION"

    def calculate_signal(self, ohlcv: dict) -> float:
        df = ohlcv.get('1h')
        if df is None or len(df) < 50:
            return 0.0
        close = df['close']

        sma20 = close.rolling(20).mean()
        std20 = close.rolling(20).std()
        bb_pos = (close.iloc[-1] - sma20.iloc[-1]) / (2 * std20.iloc[-1] + 1e-9)

        rsi = self._rsi(close, 14).iloc[-1]
        rsi_score = -(rsi - 50) / 50  # +1 at RSI=0, -1 at RSI=100

        score = -0.6 * bb_pos + 0.4 * rsi_score
        return self._clip(score)
