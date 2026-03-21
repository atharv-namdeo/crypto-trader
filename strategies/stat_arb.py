"""STAT_ARB — Statistical Arbitrage. Z-score of price vs SMA as mean-reversion signal."""
import numpy as np
from strategies.base import BaseStrategy

class StatArb(BaseStrategy):
    NAME = "STAT_ARB"

    def calculate_signal(self, ohlcv: dict) -> float:
        df = ohlcv.get('1h')
        if df is None or len(df) < 60:
            return 0.0
        close = df['close']

        sma60 = close.rolling(60).mean()
        std60 = close.rolling(60).std()
        z = (close.iloc[-1] - sma60.iloc[-1]) / (std60.iloc[-1] + 1e-9)

        # High z = overbought → sell, low z = oversold → buy
        score = float(-np.tanh(z * 0.5))
        return self._clip(score)
