import pandas as pd
import utils.indicators as ta
from strategies.base import BaseStrategy

class ParabolicSAR(BaseStrategy):
    """
    ALGO 15 — PARABOLIC SAR (CONTINUATION)
    Tier: INTRADAY / SWING | Timeframe: 1h, 4h
    Focus: Riding trends with a robust trailing stop-loss mechanism.
    """
    
    NAME = "PSAR"
    TIER = "INTRADAY"
    REGIME_GATE = ['TRENDING_BULL', 'TRENDING_BEAR']
    
    def calculate_signal(self, df: pd.DataFrame, portfolio_value: float = 1000, **kwargs) -> dict:
        """
        Input: 1h or 4h OHLCV DataFrame
        """
        if len(df) < 50:
            return {'direction': 'NONE', 'reason': 'Insufficient data'}

        df = df.copy()
        # 1. Indicator
        df['psar'] = ta.psar(df)
        df['atr'] = ta.atr(df['high'], df['low'], df['close'], length=14)

        # Latest values
        price = df['close'].iloc[-1]
        prev_price = df['close'].iloc[-2]
        sar = df['psar'].iloc[-1]
        prev_sar = df['psar'].iloc[-2]
        atr = df['atr'].iloc[-1]

        # 2. Logic: LONG (SAR flips below price)
        if prev_price < prev_sar and price > sar:
            sl = sar # PSAR is the stop loss
            tp = price + (4.0 * atr)
            qty = self.calculate_position_size(portfolio_value, 1.0, price, sl)
            return {
                'direction': 'LONG',
                'entry': price,
                'sl': sl,
                'tp': tp,
                'qty': qty,
                'reason': 'PSAR: Bullish Flip (SAR < Price)'
            }

        # 3. Logic: SHORT (SAR flips above price)
        if prev_price > prev_sar and price < sar:
            sl = sar
            tp = price - (4.0 * atr)
            qty = self.calculate_position_size(portfolio_value, 1.0, price, sl)
            return {
                'direction': 'SHORT',
                'entry': price,
                'sl': sl,
                'tp': tp,
                'qty': qty,
                'reason': 'PSAR: Bearish Flip (SAR > Price)'
            }

        return {'direction': 'NONE', 'reason': 'No PSAR flip'}
