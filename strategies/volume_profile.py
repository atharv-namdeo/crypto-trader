"""VOLUME_PROFILE — Distance from Point of Control (POC) as mean-reversion signal."""
import numpy as np
import pandas as pd
from strategies.base import BaseStrategy

class VolumeProfile(BaseStrategy):
    NAME = "VOLUME_PROFILE"

    def calculate_signal(self, ohlcv: dict) -> float:
        df = ohlcv.get('1h')
        if df is None or len(df) < 50:
            return 0.0

        recent = df.tail(100) if len(df) >= 100 else df
        try:
            price_bins = pd.cut(recent['close'], bins=20)
            vol_by_price = recent.groupby(price_bins, observed=False)['volume'].sum()
            if vol_by_price.empty:
                return 0.0
            poc_idx = vol_by_price.idxmax()
            poc_price = poc_idx.mid
        except Exception:
            return 0.0

        current = df['close'].iloc[-1]
        atr = self._atr(df, 14).iloc[-1]
        dist = (current - poc_price) / (atr + 1e-9)

        # Far above POC = mean revert down, far below = mean revert up
        score = float(-np.tanh(dist * 0.3))
        return self._clip(score)
