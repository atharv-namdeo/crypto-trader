import pandas as pd
import utils.indicators as ta
from strategies.base import BaseStrategy

class ATRExpansion(BaseStrategy):
    """
    ALGO 12 — ATR VOLATILITY EXPANSION
    Tier: SCALP / INTRADAY | Timeframe: 15m, 1h
    Focus: Capturing explosive price breakouts after low-volatility periods.
    """
    
    NAME = "ATR_EXPANSION"
    TIER = "SCALP"
    REGIME_GATE = ['HIGH_VOLATILITY', 'BREAKOUT_PENDING']
    
    def calculate_signal(self, df: pd.DataFrame, portfolio_value: float = 1000, **kwargs) -> dict:
        """
        Input: 15m or 1h OHLCV DataFrame
        """
        if len(df) < 50:
            return {'direction': 'NONE', 'reason': 'Insufficient data'}

        df = df.copy()
        # 1. Indicators
        df['atr'] = ta.atr(df['high'], df['low'], df['close'], length=14)
        df['atr_ma'] = df['atr'].rolling(window=20).mean()
        df['ema_20'] = ta.ema(df['close'], length=20)
        
        # Latest values
        price = df['close'].iloc[-1]
        atr = df['atr'].iloc[-1]
        atr_ma = df['atr_ma'].iloc[-1]
        ema_20 = df['ema_20'].iloc[-1]
        
        # 2. Volatility Expansion Check
        # Condition: Current ATR > 1.5x Average ATR (Vol Spike)
        vol_spike = atr > 1.5 * atr_ma

        # 3. Logic: LONG
        if vol_spike and price > ema_20:
            sl = price - (2.0 * atr)
            tp = price + (4.0 * atr) # 2:1 RR
            qty = self.calculate_position_size(portfolio_value, 1.0, price, sl)
            return {
                'direction': 'LONG',
                'entry': price,
                'sl': sl,
                'tp': tp,
                'qty': qty,
                'reason': 'ATR Volatility Expansion + Price > EMA 20'
            }

        # 4. Logic: SHORT
        if vol_spike and price < ema_20:
            sl = price + (2.0 * atr)
            tp = price - (4.0 * atr)
            qty = self.calculate_position_size(portfolio_value, 1.0, price, sl)
            return {
                'direction': 'SHORT',
                'entry': price,
                'sl': sl,
                'tp': tp,
                'qty': qty,
                'reason': 'ATR Volatility Expansion + Price < EMA 20'
            }

        return {'direction': 'NONE', 'reason': 'No Vol expansion'}
