import pandas as pd
import utils.indicators as ta
from strategies.base import BaseStrategy

class PivotPoints(BaseStrategy):
    """
    ALGO 14 — PIVOT POINTS (S1/R1 REVERSION)
    Tier: INTRADAY / SCALP | Timeframe: 15m, 1h
    Focus: Reversals from key institutional levels (S1, S2, R1, R2).
    """
    
    NAME = "PIVOT_POINTS"
    TIER = "SCALP"
    REGIME_GATE = ['MEAN_REVERTING', 'CHOPPY_NOISE']
    
    def calculate_signal(self, df: pd.DataFrame, portfolio_value: float = 1000, **kwargs) -> dict:
        """
        Input: 15m or 1h OHLCV DataFrame
        """
        if len(df) < 20:
            return {'direction': 'NONE', 'reason': 'Insufficient data'}

        # Calculate daily pivots from the current DF (simplified for intraday)
        pivots = ta.pivot_points(df)
        price = df['close'].iloc[-1]
        atr = ta.atr(df['high'], df['low'], df['close'], length=14).iloc[-1]

        # 1. Logic: LONG (Bounce from S1)
        if price <= pivots['S1'] and price > pivots['S2']:
            sl = pivots['S2'] - (0.1 * atr)
            tp = pivots['P'] # Target the central pivot
            qty = self.calculate_position_size(portfolio_value, 0.5, price, sl)
            return {
                'direction': 'LONG',
                'entry': price,
                'sl': sl,
                'tp': tp,
                'qty': qty,
                'reason': f'Pivot Points: Bounce from S1 ({pivots["S1"]:.2f})'
            }

        # 2. Logic: SHORT (Reject from R1)
        if price >= pivots['R1'] and price < pivots['R2']:
            sl = pivots['R2'] + (0.1 * atr)
            tp = pivots['P']
            qty = self.calculate_position_size(portfolio_value, 0.5, price, sl)
            return {
                'direction': 'SHORT',
                'entry': price,
                'sl': sl,
                'tp': tp,
                'qty': qty,
                'reason': f'Pivot Points: Reject from R1 ({pivots["R1"]:.2f})'
            }

        return {'direction': 'NONE', 'reason': 'Not at Pivot levels'}
