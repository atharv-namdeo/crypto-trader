"""TREND_EXHAUST — Trend exhaustion via RSI extremes + volume climax."""
import numpy as np
from strategies.base import BaseStrategy

class TrendExhaustion(BaseStrategy):
    NAME = "TREND_EXHAUST"

    def calculate_signal(self, ohlcv: dict) -> float:
        df = ohlcv.get('1h')
        if df is None or len(df) < 30:
            return 0.0
        close = df['close']

        rsi = self._rsi(close, 14).iloc[-1]
        vol = df['volume'].iloc[-1]
        vol_sma = df['volume'].rolling(20).mean().iloc[-1]
        vol_ratio = vol / (vol_sma + 1e-9)

        score = 0.0
        # RSI extreme + volume climax = exhaustion
        if rsi > 70:
            score -= (rsi - 70) / 30 * 0.5  # up to -0.5
            if vol_ratio > 2.0:
                score -= min(vol_ratio / 5, 0.4)  # climax reversal
        elif rsi < 30:
            score += (30 - rsi) / 30 * 0.5  # up to +0.5
            if vol_ratio > 2.0:
                score += min(vol_ratio / 5, 0.4)

        # Candle body direction
        body = close.iloc[-1] - df['open'].iloc[-1]
        atr = self._atr(df, 14).iloc[-1]
        body_score = body / (atr + 1e-9)
        score += float(np.tanh(body_score * 0.3)) * 0.15

        return self._clip(score)
