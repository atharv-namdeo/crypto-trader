import pandas as pd
import numpy as np
from enum import Enum
from typing import Dict, Any, List

class MarketPhase(Enum):
    """
    Comprehensive 10-phase market cycle classification.
    Refines basic regime detection into actionable trading states.
    """
    EARLY_BULL_BREAKOUT   = "EARLY_BULL_BREAKOUT"   # ADX rising from low, RSI crossing 50
    MATURE_BULL_EXTENSION = "MATURE_BULL_EXTENSION" # ADX > 30, High RSI, Close near channel high
    BULL_CORRECTION       = "BULL_CORRECTION"       # pullback in uptrend (EMA 20/50 support)
    ACCUMULATION          = "ACCUMULATION"          # low volatility, tight Bollinger Bands
    DISTRIBUTION          = "DISTRIBUTION"          # oscillating range, volume declining on highs
    EARLY_BEAR_BREAKDOWN  = "EARLY_BEAR_BREAKDOWN"  # ADX rising, RSI crossing below 50, below EMA
    MATURE_BEAR_DECLINE   = "MATURE_BEAR_DECLINE"   # ADX > 30, Low RSI, new lows
    BEAR_BOUNCE           = "BEAR_BOUNCE"           # oversold bounce in downtrend
    CONSOLIDATION_NARROW  = "CONSOLIDATION_NARROW"  # sideways range (low noise)
    CONSOLIDATION_WIDE    = "CONSOLIDATION_WIDE"    # sideways range (high noise/chop)
    UNKNOWN               = "UNKNOWN"

class AdvancedRegimeDetector:
    """
    10-phase market cycle detector using multi-indicator confirmation.
    Used to adjust signal confidence and position sizing.
    """
    
    def __init__(self):
        self.lookback = 100
        
    def classify_market(self, df: pd.DataFrame) -> MarketPhase:
        """
        Classifies current data into one of 10 MarketPhase states.
        """
        if df is None or len(df) < 50:
            return MarketPhase.UNKNOWN
            
        recent = df.tail(self.lookback).copy()
        current = recent.iloc[-1]
        
        # 1. Indicators (Minimal Logic for speed, assuming indicators pre-calculated or calculated here)
        rsi = self._compute_rsi(recent['close'].values)
        adx = self._compute_adx(recent)
        
        # Trend Analysis
        ema20 = recent['close'].ewm(span=20).mean().iloc[-1]
        ema50 = recent['close'].ewm(span=50).mean().iloc[-1]
        is_uptrend = ema20 > ema50
        
        # Volatility Analysis (Bollinger Band Width)
        sma20 = recent['close'].rolling(20).mean()
        std20 = recent['close'].rolling(20).std()
        bb_upper = sma20 + (2 * std20)
        bb_lower = sma20 - (2 * std20)
        # Using the last available values
        bbw = (bb_upper.iloc[-1] - bb_lower.iloc[-1]) / sma20.iloc[-1] if sma20.iloc[-1] != 0 else 0
        
        # 2. Phase Classification Engine
        if is_uptrend:
            if adx > 25 and rsi > 55:
                # Bulls in control
                if current['close'] > bb_upper.iloc[-2]: 
                    return MarketPhase.EARLY_BULL_BREAKOUT if adx < 40 else MarketPhase.MATURE_BULL_EXTENSION
                return MarketPhase.MATURE_BULL_EXTENSION
            if rsi < 50:
                return MarketPhase.BULL_CORRECTION
                
        else: # Downtrend structure
            if adx > 25 and rsi < 45:
                # Bears in control
                if current['close'] < bb_lower.iloc[-2]:
                    return MarketPhase.EARLY_BEAR_BREAKDOWN if adx < 40 else MarketPhase.MATURE_BEAR_DECLINE
                return MarketPhase.MATURE_BEAR_DECLINE
            if rsi > 50:
                return MarketPhase.BEAR_BOUNCE
        
        # 3. Sideways / Range / Accumulation
        if bbw < 0.015: # Very tight Bbw
            return MarketPhase.ACCUMULATION
        
        if bbw > 0.04: # Wide Bbw
            return MarketPhase.CONSOLIDATION_WIDE
            
        return MarketPhase.CONSOLIDATION_NARROW

    def get_risk_multiplier(self, phase: MarketPhase) -> float:
        """
        Returns a multiplier for position size based on current market phase logic.
        """
        multipliers = {
            MarketPhase.EARLY_BULL_BREAKOUT:   1.5,
            MarketPhase.MATURE_BULL_EXTENSION: 1.0,
            MarketPhase.BULL_CORRECTION:       0.8, # Wait for reversal
            MarketPhase.ACCUMULATION:          0.4, # Low conviction
            MarketPhase.DISTRIBUTION:          0.3, # High risk
            MarketPhase.EARLY_BEAR_BREAKDOWN:  1.2, # Shorting potential
            MarketPhase.MATURE_BEAR_DECLINE:   0.6, # Cautious shorts
            MarketPhase.BEAR_BOUNCE:           0.5, # Counter-trend
            MarketPhase.CONSOLIDATION_NARROW:  0.8,
            MarketPhase.CONSOLIDATION_WIDE:    0.2, # Avoid chop
            MarketPhase.UNKNOWN:               0.1
        }
        return multipliers.get(phase, 0.1)

    def _compute_rsi(self, prices, period=14):
        if len(prices) < period: return 50
        deltas = np.diff(prices)
        up = deltas[deltas > 0].sum()
        down = -deltas[deltas < 0].sum()
        if down == 0: return 100
        rs = up / (down + 1e-9)
        return 100 - (100 / (1 + rs))

    def _compute_adx(self, df, period=14):
        # Optimized ADX calculation logic
        high = df['high']
        low = df['low']
        close = df['close']
        
        plus_dm = high.diff()
        minus_dm = low.diff()
        plus_dm[plus_dm < 0] = 0
        minus_dm[minus_dm > 0] = 0
        minus_dm = abs(minus_dm)
        
        tr1 = high - low
        tr2 = abs(high - close.shift())
        tr3 = abs(low - close.shift())
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        
        atr = tr.rolling(period).mean()
        plus_di = 100 * (plus_dm.rolling(period).mean() / (atr + 1e-9))
        minus_di = 100 * (minus_dm.rolling(period).mean() / (atr + 1e-9))
        
        dx = 100 * abs(plus_di - minus_di) / (plus_di + minus_di + 1e-9)
        adx = dx.rolling(period).mean()
        
        return adx.iloc[-1] or 20
