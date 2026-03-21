"""RSI_DIV — RSI level as continuous momentum signal."""
import numpy as np
from strategies.base import BaseStrategy

class RSIDivergence(BaseStrategy):
    NAME = "RSI_DIV"

    def calculate_signal(self, ohlcv: dict) -> float:
        df = ohlcv.get('1h')
        if df is None or len(df) < 30:
            return 0.0
        close = df['close']

        rsi = self._rsi(close, 14).iloc[-1]

        # Simple RSI momentum: below 30 = buy, above 70 = sell, graded
        score = -(rsi - 50) / 50  # ranges from +1 (rsi=0) to -1 (rsi=100)

        # Check for divergence: price making new low but RSI not
        if len(close) >= 20:
            recent_price_low = close.iloc[-20:].min()
            rsi_series = self._rsi(close, 14)
            if close.iloc[-1] <= recent_price_low * 1.005:
                rsi_at_low = rsi_series.iloc[-20:].min()
                if rsi > rsi_at_low + 5:
                    score += 0.3  # bullish divergence bonus

            recent_price_high = close.iloc[-20:].max()
            if close.iloc[-1] >= recent_price_high * 0.995:
                rsi_at_high = rsi_series.iloc[-20:].max()
                if rsi < rsi_at_high - 5:
                    score -= 0.3  # bearish divergence bonus

        return self._clip(score)
