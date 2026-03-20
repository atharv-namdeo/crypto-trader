import pandas as pd
import utils.indicators as ta
from strategies.base import BaseStrategy

class VWAPReversion(BaseStrategy):
    """
    ALGO 06 — VWAP REVERSION
    Tier: INTRADAY | Timeframe: 15m, 1h
    Focus: Mean reversion of price to the daily Volume Weighted Average Price.
    """
    
    NAME = "VWAP_REVERSION"
    TIER = "INTRADAY"
    REGIME_GATE = ['MEAN_REVERTING', 'CHOPPY_NOISE']
    
    def calculate_signal(self, df: pd.DataFrame, portfolio_value: float = 1000, **kwargs) -> dict:
        """
        Input: 15m or 1h OHLCV DataFrame
        """
        if len(df) < 50:
            return {'direction': 'NONE', 'reason': 'Insufficient data'}

        df = df.copy()
        # 1. Indicator
        df['vwap'] = ta.vwap(df)
        
        # Calculate deviation (standard deviation of the average price)
        df['std'] = df['close'].rolling(window=20).std()
        df['upper_band'] = df['vwap'] + (2.0 * df['std'])
        df['lower_band'] = df['vwap'] - (2.0 * df['std'])

        # Latest values
        price = df['close'].iloc[-1]
        vwap = df['vwap'].iloc[-1]
        upper = df['upper_band'].iloc[-1]
        lower = df['lower_band'].iloc[-1]

        # 2. Logic: LONG (Price < Lower Band)
        if price < lower:
            sl = price * 0.99 # 1% SL
            tp = vwap        # TP at the value area
            qty = self.calculate_position_size(portfolio_value, 1.0, price, sl)
            return {
                'direction': 'LONG',
                'entry': price,
                'sl': sl,
                'tp': tp,
                'qty': qty,
                'reason': 'VWAP: Price below 2.0 StdDev'
            }

        # 3. Logic: SHORT (Price > Upper Band)
        if price > upper:
            sl = price * 1.01
            tp = vwap
            qty = self.calculate_position_size(portfolio_value, 1.0, price, sl)
            return {
                'direction': 'SHORT',
                'entry': price,
                'sl': sl,
                'tp': tp,
                'qty': qty,
                'reason': 'VWAP: Price above 2.0 StdDev'
            }

        return {'direction': 'NONE', 'reason': 'No VWAP extreme'}
