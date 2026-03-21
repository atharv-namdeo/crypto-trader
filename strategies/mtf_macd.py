"""MTF_MACD — Multi-timeframe MACD confluence (4h trend + 1h execution)."""
import numpy as np
from strategies.base import BaseStrategy

class MTFMACD(BaseStrategy):
    NAME = "MTF_MACD"

    def calculate_signal(self, ohlcv: dict) -> float:
        df_1h = ohlcv.get('1h')
        df_4h = ohlcv.get('4h')
        if df_1h is None or len(df_1h) < 50:
            return 0.0
        if df_4h is None or len(df_4h) < 30:
            df_4h = df_1h  # fallback

        score = 0.0
        # 4h MACD direction
        ema12_4h = df_4h['close'].ewm(span=12).mean()
        ema26_4h = df_4h['close'].ewm(span=26).mean()
        macd_4h = (ema12_4h - ema26_4h).iloc[-1]
        if macd_4h > 0: score += 0.3
        else: score -= 0.3

        # 1h MACD histogram momentum
        ema12_1h = df_1h['close'].ewm(span=12).mean()
        ema26_1h = df_1h['close'].ewm(span=26).mean()
        macd_1h = ema12_1h - ema26_1h
        sig_1h = macd_1h.ewm(span=9).mean()
        hist = macd_1h - sig_1h
        if hist.iloc[-1] > 0: score += 0.2
        else: score -= 0.2

        # Histogram trend (accelerating?)
        if len(hist) >= 2 and hist.iloc[-1] > hist.iloc[-2]:
            score += 0.15
        elif len(hist) >= 2:
            score -= 0.15

        # Confluence bonus
        if (macd_4h > 0 and hist.iloc[-1] > 0):
            score += 0.15
        elif (macd_4h < 0 and hist.iloc[-1] < 0):
            score -= 0.15

        return self._clip(score)
