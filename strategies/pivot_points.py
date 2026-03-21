"""PIVOT_POINTS — Price position relative to calculated pivot levels."""
import numpy as np
from strategies.base import BaseStrategy

class PivotPoints(BaseStrategy):
    NAME = "PIVOT_POINTS"

    def calculate_signal(self, ohlcv: dict) -> float:
        df = ohlcv.get('1h')
        if df is None or len(df) < 24:
            return 0.0

        # Use last 24 bars as "previous session"
        prev = df.iloc[-48:-24] if len(df) >= 48 else df.iloc[:len(df)//2]
        if len(prev) < 5:
            return 0.0

        h = prev['high'].max()
        l = prev['low'].min()
        c = prev['close'].iloc[-1]
        pivot = (h + l + c) / 3
        r1 = 2 * pivot - l
        s1 = 2 * pivot - h

        price = df['close'].iloc[-1]
        rng = r1 - s1 + 1e-9

        # Score based on position: near S1 = buy, near R1 = sell
        pos = (price - s1) / rng  # 0=at S1, 1=at R1
        score = -(pos - 0.5) * 1.2  # convert to [-0.6, +0.6]

        return self._clip(score)
