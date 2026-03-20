import pandas as pd
import numpy as np
import utils.indicators as ta
from strategies.base import BaseStrategy

class RSIDivergence(BaseStrategy):
    """
    ALGO 09 — RSI DIVERGENCE
    Tier: SCALP / INTRADAY | Timeframe: 15m, 1h
    Focus: Detecting trend exhaustion and reversals via price-momentum divergence.
    """
    
    NAME = "RSI_DIV"
    TIER = "INTRADAY"
    REGIME_GATE = ['MEAN_REVERTING', 'TRENDING_BULL', 'TRENDING_BEAR']
    
    def calculate_signal(self, df: pd.DataFrame, portfolio_value: float = 1000, **kwargs) -> dict:
        """
        Input: 15m or 1h OHLCV DataFrame
        """
        if len(df) < 60:
            return {'direction': 'NONE', 'reason': 'Insufficient data'}

        df = df.copy()
        df['rsi'] = ta.rsi(df['close'], length=14)
        df['atr'] = ta.atr(df['high'], df['low'], df['close'], length=14)
        
        # 1. Detect Pivots (Approximate)
        # Using a simple peak/trough detector
        df['price_high'] = (df['high'] == df['high'].rolling(10, center=True).max())
        df['price_low'] = (df['low'] == df['low'].rolling(10, center=True).min())
        df['rsi_high'] = (df['rsi'] == df['rsi'].rolling(10, center=True).max())
        df['rsi_low'] = (df['rsi'] == df['rsi'].rolling(10, center=True).min())

        # Extract recent pivots
        highs = df[df['price_high']].tail(2)
        lows = df[df['price_low']].tail(2)

        if len(highs) < 2 or len(lows) < 2:
            return {'direction': 'NONE', 'reason': 'No pivots found'}

        price = df['close'].iloc[-1]
        atr = df['atr'].iloc[-1]

        # 2. Bearish Divergence (Price HH, RSI LH)
        if highs['high'].iloc[-1] > highs['high'].iloc[-2] and \
           highs['rsi'].iloc[-1] < highs['rsi'].iloc[-2]:
            sl = price + (1.5 * atr)
            tp = price - (3.0 * atr)
            qty = self.calculate_position_size(portfolio_value, 1.0, price, sl)
            return {
                'direction': 'SHORT',
                'entry': price,
                'sl': sl,
                'tp': tp,
                'qty': qty,
                'reason': 'RSI Bearish Divergence (Price HH, RSI LH)'
            }

        # 3. Bullish Divergence (Price LL, RSI HL)
        if lows['low'].iloc[-1] < lows['low'].iloc[-2] and \
           lows['rsi'].iloc[-1] > lows['rsi'].iloc[-2]:
            sl = price - (1.5 * atr)
            tp = price + (3.0 * atr)
            qty = self.calculate_position_size(portfolio_value, 1.0, price, sl)
            return {
                'direction': 'LONG',
                'entry': price,
                'sl': sl,
                'tp': tp,
                'qty': qty,
                'reason': 'RSI Bullish Divergence (Price LL, RSI HL)'
            }

        return {'direction': 'NONE', 'reason': 'No divergence'}
