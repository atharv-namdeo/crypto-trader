import pandas as pd
import utils.indicators as ta
from strategies.base import BaseStrategy

class IchimokuCloud(BaseStrategy):
    """
    ALGO 11 — ICHIMOKU CLOUD (KUMO BREAKOUT)
    Tier: INTRADAY / SWING | Timeframe: 1h, 4h
    Focus: Capturing major trends confirmed by the Ichimoku equilibrium system.
    """
    
    NAME = "ICHIMOKU"
    TIER = "INTRADAY"
    REGIME_GATE = ['TRENDING_BULL', 'TRENDING_BEAR', 'BREAKOUT_PENDING']
    
    def calculate_signal(self, df: pd.DataFrame, portfolio_value: float = 1000, **kwargs) -> dict:
        """
        Input: 1h or 4h OHLCV DataFrame
        """
        if len(df) < 52:
            return {'direction': 'NONE', 'reason': 'Insufficient data'}

        df = df.copy()
        # 1. Indicator
        ich = ta.ichimoku(df)
        df['tenkan'] = ich['tenkan_sen']
        df['kijun'] = ich['kijun_sen']
        df['span_a'] = ich['senkou_span_a']
        df['span_b'] = ich['senkou_span_b']
        df['atr'] = ta.atr(df['high'], df['low'], df['close'], length=14)

        # Latest values
        price = df['close'].iloc[-1]
        tenkan = df['tenkan'].iloc[-1]
        kijun = df['kijun'].iloc[-1]
        span_a = df['span_a'].iloc[-1]
        span_b = df['span_b'].iloc[-1]
        atr = df['atr'].iloc[-1]

        # 2. Logic: LONG (Kumo Breakout)
        # Condition: Price > Cloud + Tenkan > Kijun + Bullish Cloud
        if price > max(span_a, span_b) and tenkan > kijun and span_a > span_b:
            sl = kijun # Use Kijun as SL for trend integrity
            tp = price + (4.0 * atr) # 2:1 RR approx
            qty = self.calculate_position_size(portfolio_value, 1.0, price, sl)
            return {
                'direction': 'LONG',
                'entry': price,
                'sl': sl,
                'tp': tp,
                'qty': qty,
                'reason': 'Ichimoku: Bullish Kumo Breakout + Tenkan/Kijun Confluence'
            }

        # 3. Logic: SHORT (Kumo Breakout)
        # Condition: Price < Cloud + Tenkan < Kijun + Bearish Cloud
        if price < min(span_a, span_b) and tenkan < kijun and span_a < span_b:
            sl = kijun
            tp = price - (4.0 * atr)
            qty = self.calculate_position_size(portfolio_value, 1.0, price, sl)
            return {
                'direction': 'SHORT',
                'entry': price,
                'sl': sl,
                'tp': tp,
                'qty': qty,
                'reason': 'Ichimoku: Bearish Kumo Breakout + Tenkan/Kijun Confluence'
            }

        return {'direction': 'NONE', 'reason': 'No Ichimoku signal'}
