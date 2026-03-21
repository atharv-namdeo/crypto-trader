"""GANN_FAN — Price position relative to Gann retracement levels."""
import numpy as np
from strategies.base import BaseStrategy

class GANNFan(BaseStrategy):
    NAME = "GANN_FAN"

    def calculate_signal(self, ohlcv: dict) -> float:
        df = ohlcv.get('4h')
        if df is None or len(df) < 50:
            df = ohlcv.get('1h')
        if df is None or len(df) < 50:
            return 0.0

        recent = df.tail(100) if len(df) >= 100 else df
        swing_low = recent['low'].min()
        swing_high = recent['high'].max()
        rng = swing_high - swing_low
        if rng < 1e-9:
            return 0.0

        price = df['close'].iloc[-1]
        # Gann levels at 25%, 50%, 75%
        gann_25 = swing_low + rng * 0.25
        gann_50 = swing_low + rng * 0.50
        gann_75 = swing_low + rng * 0.75

        # Score: near 25% = buy zone, near 75% = sell zone, 50% = neutral
        pos = (price - swing_low) / rng  # 0 to 1
        score = -(pos - 0.5) * 1.0  # centered at 0.5 → [-0.5, +0.5]

        # Strengthen near extreme Gann levels
        if price < gann_25: score += 0.2
        elif price > gann_75: score -= 0.2

        return self._clip(score)
