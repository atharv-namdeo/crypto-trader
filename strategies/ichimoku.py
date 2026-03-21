"""ICHIMOKU — Cloud-based trend direction and strength."""
import numpy as np
from strategies.base import BaseStrategy

class IchimokuCloud(BaseStrategy):
    NAME = "ICHIMOKU"

    def calculate_signal(self, ohlcv: dict) -> float:
        df = ohlcv.get('1h')
        if df is None or len(df) < 52:
            return 0.0
        high, low, close = df['high'], df['low'], df['close']

        # Tenkan-sen (9-period)
        tenkan = (high.rolling(9).max() + low.rolling(9).min()) / 2
        # Kijun-sen (26-period)
        kijun = (high.rolling(26).max() + low.rolling(26).min()) / 2
        # Senkou Span A & B
        span_a = ((tenkan + kijun) / 2).shift(26)
        span_b = ((high.rolling(52).max() + low.rolling(52).min()) / 2).shift(26)

        price = close.iloc[-1]
        t = tenkan.iloc[-1]
        k = kijun.iloc[-1]
        sa = span_a.iloc[-1] if not np.isnan(span_a.iloc[-1]) else price
        sb = span_b.iloc[-1] if not np.isnan(span_b.iloc[-1]) else price
        cloud_top = max(sa, sb)
        cloud_bot = min(sa, sb)

        score = 0.0
        # Price vs cloud
        if price > cloud_top: score += 0.35
        elif price < cloud_bot: score -= 0.35
        # Tenkan vs Kijun
        if t > k: score += 0.25
        else: score -= 0.25
        # Cloud is bullish (span_a > span_b)
        if sa > sb: score += 0.15
        else: score -= 0.15
        # Distance from cloud as conviction
        cloud_mid = (cloud_top + cloud_bot) / 2
        atr = self._atr(df, 14).iloc[-1]
        dist = (price - cloud_mid) / (atr + 1e-9)
        score += float(np.tanh(dist * 0.1)) * 0.25

        return self._clip(score)
