"""MTF — Momentum Trend Following. EMA crossover + RSI + MACD + Volume."""
import numpy as np
from strategies.base import BaseStrategy

class MomentumTrendFollowing(BaseStrategy):
    NAME = "MTF"

    def calculate_signal(self, ohlcv: dict) -> float:
        df = ohlcv.get('1h')
        if df is None or len(df) < 50:
            return 0.0
        close = df['close']
        score = 0.0

        ema9 = close.ewm(span=9).mean()
        ema21 = close.ewm(span=21).mean()
        if ema9.iloc[-1] > ema21.iloc[-1]:
            score += 0.3
        else:
            score -= 0.3

        rsi = self._rsi(close, 14)
        r = rsi.iloc[-1]
        if r > 55: score += 0.2
        elif r < 45: score -= 0.2

        macd_line = ema9 - ema21
        if macd_line.iloc[-1] > macd_line.iloc[-2]:
            score += 0.2
        else:
            score -= 0.2

        vol_sma = df['volume'].rolling(20).mean()
        vol_ratio = df['volume'].iloc[-1] / (vol_sma.iloc[-1] + 1e-9)
        if vol_ratio > 1.2:
            score *= 1.2

        return self._clip(score)
