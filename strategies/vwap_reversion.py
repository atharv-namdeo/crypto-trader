"""VWAP_REVERSION — Distance from VWAP as mean-reversion signal."""
import numpy as np
from strategies.base import BaseStrategy

class VWAPReversion(BaseStrategy):
    NAME = "VWAP_REVERSION"

    def calculate_signal(self, ohlcv: dict) -> float:
        df = ohlcv.get('1h')
        if df is None or len(df) < 30:
            return 0.0
        close = df['close']
        vol = df['volume']
        typical = (df['high'] + df['low'] + close) / 3
        cum_vol = vol.cumsum()
        vwap = (typical * vol).cumsum() / (cum_vol + 1e-9)
        std = (close - vwap).rolling(20).std()

        dist = (close.iloc[-1] - vwap.iloc[-1]) / (std.iloc[-1] + 1e-9)
        score = float(-np.tanh(dist * 0.4))
        return self._clip(score)
