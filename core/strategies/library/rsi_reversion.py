import pandas as pd
import numpy as np
from typing import Dict, Any

class RSIReversionStrategy:
    """
    RSI Mean Reversion Strategy
    """
    @staticmethod
    def generate(df: pd.DataFrame, phase) -> Dict[str, Any]:
        if df is None or len(df) < 20:
            return {"action": "NEUTRAL", "score": 0.5}

        closes   = df["close"].values
        rsi_now  = RSIReversionStrategy._calculate_rsi(closes)
        rsi_prev = RSIReversionStrategy._calculate_rsi(closes[:-1])

        # Import phase enum context
        # Bullish regimes
        is_bullish = phase.value in ("TRENDING_BULL", "RANGING_BULL", "VOLATILE_BULL", "EXPLOSION", "COMPRESSION")

        if is_bullish:
            if rsi_prev < 35 and rsi_now >= 35:
                return {"action": "BUY", "score": 0.72, "rsi": rsi_now}
            if rsi_now < 45:
                return {"action": "BUY", "score": 0.60, "rsi": rsi_now}

        return {"action": "NEUTRAL", "score": 0.5, "rsi": rsi_now}

    @staticmethod
    def _calculate_rsi(prices, period: int = 14) -> float:
        if len(prices) < period:
            return 50.0
        deltas = np.diff(prices)
        up     = deltas[deltas > 0].sum()
        down   = -deltas[deltas < 0].sum()
        if down == 0:
            return 100.0
        rs = up / (down + 1e-9)
        return float(100 - (100 / (1 + rs)))
