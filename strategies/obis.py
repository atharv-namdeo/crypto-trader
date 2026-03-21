"""OBIS — Order Book Imbalance Score. Uses volume ratio as proxy when no order book."""
import numpy as np
from strategies.base import BaseStrategy

class OrderBookImbalance(BaseStrategy):
    NAME = "OBIS"

    def calculate_signal(self, ohlcv: dict) -> float:
        df = ohlcv.get('1m')
        if df is None or len(df) < 20:
            df = ohlcv.get('5m')
        if df is None or len(df) < 20:
            return 0.0

        # Use buy/sell volume proxy: close > open = buy volume, else sell
        recent = df.tail(20)
        buy_vol = recent.loc[recent['close'] >= recent['open'], 'volume'].sum()
        sell_vol = recent.loc[recent['close'] < recent['open'], 'volume'].sum()
        total = buy_vol + sell_vol + 1e-9

        imbalance = (buy_vol - sell_vol) / total  # [-1, +1]
        score = float(imbalance * 0.8)
        return self._clip(score)
