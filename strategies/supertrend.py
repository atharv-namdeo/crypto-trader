import pandas as pd
import utils.indicators as ta
from strategies.base import BaseStrategy

class SupertrendStrategy(BaseStrategy):
    """
    ALGO 16 — SUPERTREND (TREND FOLLOWING)
    Tier: INTRADAY / SWING | Timeframe: 1h, 4h
    Focus: High-confidence trend confirmation using ATR-adjusted price bands.
    """
    
    NAME = "SUPERTREND"
    TIER = "INTRADAY"
    REGIME_GATE = ['TRENDING_BULL', 'TRENDING_BEAR', 'BREAKOUT_PENDING']
    
    def calculate_signal(self, df: pd.DataFrame, portfolio_value: float = 1000, **kwargs) -> dict:
        """
        Input: 1h or 4h OHLCV DataFrame
        """
        if len(df) < 50:
            return {'direction': 'NONE', 'reason': 'Insufficient data'}

        df = df.copy()
        # 1. Indicator
        st = ta.supertrend(df, period=10, multiplier=3)
        df['st_upper'] = st['upper']
        df['st_lower'] = st['lower']
        df['atr'] = ta.atr(df['high'], df['low'], df['close'], length=14)

        # Latest values
        price = df['close'].iloc[-1]
        prev_price = df['close'].iloc[-2]
        upper = df['st_upper'].iloc[-1]
        lower = df['st_lower'].iloc[-1]
        prev_upper = df['st_upper'].iloc[-2]
        prev_lower = df['st_lower'].iloc[-2]
        atr = df['atr'].iloc[-1]

        # 2. Logic: LONG (Price crosses above Upper Band - Breakout)
        if prev_price <= prev_upper and price > upper:
            sl = lower # Theoretical lower band as SL
            tp = price + (4.0 * atr)
            qty = self.calculate_position_size(portfolio_value, 1.0, price, sl)
            return {
                'direction': 'LONG',
                'entry': price,
                'sl': sl,
                'tp': tp,
                'qty': qty,
                'reason': 'Supertrend: Bullish Breakout'
            }

        # 3. Logic: SHORT (Price crosses below Lower Band)
        if prev_price >= prev_lower and price < lower:
            sl = upper
            tp = price - (4.0 * atr)
            qty = self.calculate_position_size(portfolio_value, 1.0, price, sl)
            return {
                'direction': 'SHORT',
                'entry': price,
                'sl': sl,
                'tp': tp,
                'qty': qty,
                'reason': 'Supertrend: Bearish Breakout'
            }

        return {'direction': 'NONE', 'reason': 'Within Supertrend bands'}
