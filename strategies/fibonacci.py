"""FIBONACCI — Price position relative to Fibonacci retracement levels."""
import numpy as np
from strategies.base import BaseStrategy

class FibonacciRetracement(BaseStrategy):
    NAME = "FIBONACCI"

    def calculate_signal(self, ohlcv: dict) -> float:
        df = ohlcv.get('1h')
        if df is None or len(df) < 100:
            return 0.0

        recent = df.tail(100)
        swing_low = recent['low'].min()
        swing_high = recent['high'].max()
        diff = swing_high - swing_low
        if diff < 1e-9:
            return 0.0

        price = df['close'].iloc[-1]
        # Position within the range: 0 = at low, 1 = at high
        pos = (price - swing_low) / diff

        # Fibonacci zones: near 0.382/0.618 are buy zones in uptrend
        fib_618 = swing_low + 0.618 * diff
        fib_382 = swing_low + 0.382 * diff

        # Determine trend direction from swing order
        high_idx = recent['high'].idxmax()
        low_idx = recent['low'].idxmin()
        is_uptrend = high_idx > low_idx

        if is_uptrend:
            # In uptrend, below 0.618 = buy opportunity
            if price < fib_618:
                score = (fib_618 - price) / (diff * 0.5 + 1e-9) * 0.6
            else:
                score = 0.1  # still mildly bullish in uptrend
        else:
            # In downtrend, above 0.382 = sell opportunity
            if price > fib_382:
                score = -(price - fib_382) / (diff * 0.5 + 1e-9) * 0.6
            else:
                score = -0.1  # still mildly bearish in downtrend

        return self._clip(score)
