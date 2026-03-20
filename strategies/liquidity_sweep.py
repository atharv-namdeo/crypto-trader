import pandas as pd
import utils.indicators as ta
from strategies.base import BaseStrategy

class LiquiditySweep(BaseStrategy):
    """
    ALGO 07 — LIQUIDITY SWEEP (LS)
    Tier: SCALP / INTRADAY | Timeframe: 15m, 1h
    Focus: Capturing reversals after "Stop Hunts" or sweeps of key levels.
    """
    
    NAME = "LIQUIDITY_SWEEP"
    TIER = "SCALP"
    REGIME_GATE = ['BREAKOUT_PENDING', 'MEAN_REVERTING']
    
    def calculate_signal(self, df: pd.DataFrame, portfolio_value: float = 1000, **kwargs) -> dict:
        """
        Input: 15m or 1h OHLCV DataFrame
        """
        if len(df) < 50:
            return {'direction': 'NONE', 'reason': 'Insufficient data'}

        df = df.copy()
        # 1. Swing Levels (20 period)
        df['swing_high'] = df['high'].shift().rolling(window=20).max()
        df['swing_low'] = df['low'].shift().rolling(window=20).min()
        df['atr'] = ta.atr(df['high'], df['low'], df['close'], length=14)

        # Latest values
        price = df['close'].iloc[-1]
        prev_price = df['close'].iloc[-2]
        low = df['low'].iloc[-1]
        high = df['high'].iloc[-1]
        swing_high = df['swing_high'].iloc[-1]
        swing_low = df['swing_low'].iloc[-1]
        atr = df['atr'].iloc[-1]

        # 2. Logic: LONG Sweep
        # Condition: Current Low went < Swing Low, but Current Close is > Swing Low
        if low < swing_low and price > swing_low:
            sl = price - (1.5 * atr)
            tp = swing_high # Target the other side
            qty = self.calculate_position_size(portfolio_value, 1.0, price, sl)
            return {
                'direction': 'LONG',
                'entry': price,
                'sl': sl,
                'tp': tp,
                'qty': qty,
                'reason': f'Liquidity Sweep: Low ({low:.2f}) < Swing Low'
            }

        # 3. Logic: SHORT Sweep
        # Condition: Current High went > Swing High, but Current Close is < Swing High
        if high > swing_high and price < swing_high:
            sl = price + (1.5 * atr)
            tp = swing_low
            qty = self.calculate_position_size(portfolio_value, 1.0, price, sl)
            return {
                'direction': 'SHORT',
                'entry': price,
                'sl': sl,
                'tp': tp,
                'qty': qty,
                'reason': f'Liquidity Sweep: High ({high:.2f}) > Swing High'
            }

        return {'direction': 'NONE', 'reason': 'No sweep detected'}
