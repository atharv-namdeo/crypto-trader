"""
strategies/base.py
Base class for all strategies — Phase 2 (Score-based)
"""

import numpy as np


class BaseStrategy:
    """All strategies return a float score ∈ [-1.0, +1.0]."""

    NAME = "Base"

    def calculate_signal(self, ohlcv: dict) -> float:
        """
        Args:
            ohlcv: {
                '1m':  DataFrame [open, high, low, close, volume],
                '5m':  DataFrame,
                '15m': DataFrame,
                '1h':  DataFrame,
                '4h':  DataFrame,
            }
        Returns:
            float between -1.0 (strong sell) and +1.0 (strong buy)
        """
        return 0.0

    @staticmethod
    def _clip(score: float) -> float:
        return float(np.clip(score, -1.0, 1.0))

    @staticmethod
    def _rsi(series, period=14):
        delta = series.diff()
        gain = delta.clip(lower=0).rolling(period).mean()
        loss = (-delta.clip(upper=0)).rolling(period).mean()
        rs = gain / (loss + 1e-9)
        return 100 - (100 / (1 + rs))

    @staticmethod
    def _atr(df, period=14):
        hl = df['high'] - df['low']
        hc = (df['high'] - df['close'].shift()).abs()
        lc = (df['low'] - df['close'].shift()).abs()
        import pandas as pd
        tr = pd.concat([hl, hc, lc], axis=1).max(axis=1)
        return tr.rolling(period).mean()
