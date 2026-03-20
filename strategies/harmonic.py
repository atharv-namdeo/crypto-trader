import pandas as pd
import numpy as np
import utils.indicators as ta
from strategies.base import BaseStrategy

class HarmonicPatterns(BaseStrategy):
    """
    ALGO 18 — HARMONIC PATTERNS (XABCD)
    Tier: INTRADAY / SWING | Timeframe: 1h, 4h
    Focus: Detecting Gartley/Butterfly/Bat harmonic patterns for reversal entries.
    """
    
    NAME = "HARMONIC"
    TIER = "INTRADAY"
    REGIME_GATE = ['MEAN_REVERTING', 'TRENDING_BULL', 'TRENDING_BEAR']
    
    def calculate_signal(self, df: pd.DataFrame, portfolio_value: float = 1000, **kwargs) -> dict:
        if len(df) < 60:
            return {'direction': 'NONE', 'reason': 'Insufficient data'}

        df = df.copy()
        # 1. Detect 5 Swing Points (X, A, B, C, D)
        df['swing_h'] = (df['high'] == df['high'].rolling(10, center=True).max())
        df['swing_l'] = (df['low'] == df['low'].rolling(10, center=True).min())
        
        highs = df[df['swing_h']].tail(3)
        lows = df[df['swing_l']].tail(3)
        
        if len(highs) < 2 or len(lows) < 2:
            return {'direction': 'NONE', 'reason': 'Not enough pivots'}
        
        price = df['close'].iloc[-1]
        atr = ta.atr(df['high'], df['low'], df['close'], length=14).iloc[-1]
        
        # 2. Simplified Gartley Detection (Bullish)
        # XA leg, AB retracement (0.618), BC extension, CD completion
        x = lows['low'].iloc[-2]
        a = highs['high'].iloc[-2]
        b = lows['low'].iloc[-1]
        
        xa = a - x
        ab = a - b
        
        if xa == 0: return {'direction': 'NONE'}
        
        ab_ratio = ab / xa
        
        # Bullish Gartley: AB retraces 0.618 of XA
        if 0.55 <= ab_ratio <= 0.72 and price <= b * 1.005:
            sl = x - (0.5 * atr)
            tp = a  # Target the A point
            qty = self.calculate_position_size(portfolio_value, 1.0, price, sl)
            return {
                'direction': 'LONG', 'entry': price, 'sl': sl, 'tp': tp,
                'qty': qty, 'reason': f'Harmonic: Bullish Gartley (AB/XA={ab_ratio:.3f})'
            }
        
        # 3. Bearish Gartley
        x2 = highs['high'].iloc[-2]
        a2 = lows['low'].iloc[-2]
        b2 = highs['high'].iloc[-1]
        
        xa2 = x2 - a2
        ab2 = b2 - a2
        
        if xa2 == 0: return {'direction': 'NONE'}
        
        ab_ratio2 = ab2 / xa2
        
        if 0.55 <= ab_ratio2 <= 0.72 and price >= b2 * 0.995:
            sl = x2 + (0.5 * atr)
            tp = a2
            qty = self.calculate_position_size(portfolio_value, 1.0, price, sl)
            return {
                'direction': 'SHORT', 'entry': price, 'sl': sl, 'tp': tp,
                'qty': qty, 'reason': f'Harmonic: Bearish Gartley (AB/XA={ab_ratio2:.3f})'
            }

        return {'direction': 'NONE', 'reason': 'No harmonic pattern'}
