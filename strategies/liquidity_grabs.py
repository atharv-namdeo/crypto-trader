import pandas as pd
import utils.indicators as ta
from strategies.base import BaseStrategy

class LiquidityGrabs(BaseStrategy):
    """
    ALGO 19 — LIQUIDITY GRABS (SMART MONEY)
    Tier: SCALP / INTRADAY | Timeframe: 15m, 1h
    Focus: Detecting institutional order flow by identifying false breakouts
    at equal highs/lows where retail stops cluster.
    """
    
    NAME = "LIQUIDITY_GRAB"
    TIER = "SCALP"
    REGIME_GATE = ['MEAN_REVERTING', 'BREAKOUT_PENDING', 'HIGH_VOLATILITY']
    
    def calculate_signal(self, df: pd.DataFrame, portfolio_value: float = 1000, **kwargs) -> dict:
        if len(df) < 50:
            return {'direction': 'NONE', 'reason': 'Insufficient data'}

        df = df.copy()
        df['atr'] = ta.atr(df['high'], df['low'], df['close'], length=14)
        
        price = df['close'].iloc[-1]
        high = df['high'].iloc[-1]
        low = df['low'].iloc[-1]
        atr = df['atr'].iloc[-1]
        
        # 1. Detect Equal Highs/Lows (Liquidity Pools)
        recent = df.tail(30)
        tolerance = atr * 0.3
        
        # Equal Highs (Sell-Side Liquidity)
        max_high = recent['high'].max()
        equal_highs = recent[abs(recent['high'] - max_high) < tolerance]
        
        # Equal Lows (Buy-Side Liquidity)
        min_low = recent['low'].min()
        equal_lows = recent[abs(recent['low'] - min_low) < tolerance]
        
        # 2. Logic: LONG (Grab below equal lows then reverse)
        if len(equal_lows) >= 2 and low < min_low and price > min_low:
            sl = low - (0.5 * atr)
            tp = price + (3.0 * atr)
            qty = self.calculate_position_size(portfolio_value, 1.0, price, sl)
            return {
                'direction': 'LONG', 'entry': price, 'sl': sl, 'tp': tp,
                'qty': qty, 'reason': f'Liquidity Grab: Below equal lows ({min_low:.2f})'
            }

        # 3. Logic: SHORT (Grab above equal highs then reverse)
        if len(equal_highs) >= 2 and high > max_high and price < max_high:
            sl = high + (0.5 * atr)
            tp = price - (3.0 * atr)
            qty = self.calculate_position_size(portfolio_value, 1.0, price, sl)
            return {
                'direction': 'SHORT', 'entry': price, 'sl': sl, 'tp': tp,
                'qty': qty, 'reason': f'Liquidity Grab: Above equal highs ({max_high:.2f})'
            }

        return {'direction': 'NONE', 'reason': 'No liquidity grab'}
