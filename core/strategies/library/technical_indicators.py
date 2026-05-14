import pandas as pd
import numpy as np
from typing import Dict, Any

class TechnicalStrategies:
    """
    Unified library for the 20+ 'Legacy' strategies.
    Restored for Phase 11 Omega Brain integration.
    """

    @staticmethod
    def ichimoku(df: pd.DataFrame) -> Dict[str, Any]:
        if len(df) < 52: return {"action": "HOLD", "score": 0.5}
        c = df['close']
        h = df['high']
        l = df['low']
        
        tenkan = (h.rolling(9).max() + l.rolling(9).min()) / 2
        kijun = (h.rolling(26).max() + l.rolling(26).min()) / 2
        
        sig = 0.5
        if tenkan.iloc[-1] > kijun.iloc[-1] and c.iloc[-1] > tenkan.iloc[-1]:
            sig = 0.8 # Bullish
        elif tenkan.iloc[-1] < kijun.iloc[-1] and c.iloc[-1] < tenkan.iloc[-1]:
            sig = 0.2 # Bearish
            
        return {"action": "BUY" if sig > 0.7 else "SELL" if sig < 0.3 else "HOLD", "score": sig}

    @staticmethod
    def supertrend(df: pd.DataFrame, period: int = 10, multiplier: float = 3.0) -> Dict[str, Any]:
        if len(df) < period: return {"action": "HOLD", "score": 0.5}
        from core.utils import compute_atr
        atr = compute_atr(df, period)
        
        mid = (df['high'] + df['low']) / 2
        upper = mid + (multiplier * atr)
        lower = mid - (multiplier * atr)
        
        # Simplified trend detection
        curr_close = df['close'].iloc[-1]
        if curr_close > upper.iloc[-1]: return {"action": "BUY", "score": 0.8}
        if curr_close < lower.iloc[-1]: return {"action": "SELL", "score": 0.2}
        return {"action": "HOLD", "score": 0.5}

    @staticmethod
    def macd(df: pd.DataFrame) -> Dict[str, Any]:
        c = df['close']
        ema12 = c.ewm(span=12).mean()
        ema26 = c.ewm(span=26).mean()
        macd_line = ema12 - ema26
        signal_line = macd_line.ewm(span=9).mean()
        
        if macd_line.iloc[-1] > signal_line.iloc[-1] and macd_line.iloc[-2] <= signal_line.iloc[-2]:
            return {"action": "BUY", "score": 0.75}
        if macd_line.iloc[-1] < signal_line.iloc[-1] and macd_line.iloc[-2] >= signal_line.iloc[-2]:
            return {"action": "SELL", "score": 0.25}
        return {"action": "HOLD", "score": 0.5}

    @staticmethod
    def bbands(df: pd.DataFrame) -> Dict[str, Any]:
        c = df['close']
        sma = c.rolling(20).mean()
        std = c.rolling(20).std()
        upper = sma + (2 * std)
        lower = sma - (2 * std)
        
        curr = c.iloc[-1]
        if curr < lower.iloc[-1]: return {"action": "BUY", "score": 0.7} # Oversold
        if curr > upper.iloc[-1]: return {"action": "SELL", "score": 0.3} # Overbought
        return {"action": "HOLD", "score": 0.5}

    @staticmethod
    def psar(df: pd.DataFrame) -> Dict[str, Any]:
        # Simplified PSAR approximation for direction
        c = df['close']
        ema20 = c.ewm(span=20).mean()
        if c.iloc[-1] > ema20.iloc[-1]: return {"action": "BUY", "score": 0.6}
        return {"action": "SELL", "score": 0.4}

    @staticmethod
    def pivot_points(df: pd.DataFrame) -> Dict[str, Any]:
        # Daily Pivots
        prev_h = df['high'].iloc[-2]
        prev_l = df['low'].iloc[-2]
        prev_c = df['close'].iloc[-2]
        
        pp = (prev_h + prev_l + prev_c) / 3
        s1 = (2 * pp) - prev_h
        r1 = (2 * pp) - prev_l
        
        curr = df['close'].iloc[-1]
        if curr < s1: return {"action": "BUY", "score": 0.75}
        if curr > r1: return {"action": "SELL", "score": 0.25}
        return {"action": "HOLD", "score": 0.5}

    @staticmethod
    def ultimate_oscillator(df: pd.DataFrame) -> Dict[str, Any]:
        from core.utils import compute_ultosc
        uo = compute_ultosc(df)
        val = uo.iloc[-1]
        if val < 30: return {"action": "BUY", "score": 0.7}
        if val > 70: return {"action": "SELL", "score": 0.3}
        return {"action": "HOLD", "score": 0.5}

    @staticmethod
    def williams_r(df: pd.DataFrame, period: int = 14) -> Dict[str, Any]:
        h = df['high'].rolling(period).max()
        l = df['low'].rolling(period).min()
        c = df['close']
        wr = -100 * (h - c) / (h - l + 1e-9)
        val = wr.iloc[-1]
        if val < -80: return {"action": "BUY", "score": 0.7}
        if val > -20: return {"action": "SELL", "score": 0.3}
        return {"action": "HOLD", "score": 0.5}

    @staticmethod
    def chaikin_money_flow(df: pd.DataFrame, period: int = 20) -> Dict[str, Any]:
        mfm = ((df['close'] - df['low']) - (df['high'] - df['close'])) / (df['high'] - df['low'] + 1e-9)
        mfv = mfm * df['volume']
        cmf = mfv.rolling(period).sum() / df['volume'].rolling(period).sum()
        val = cmf.iloc[-1]
        if val > 0.1: return {"action": "BUY", "score": 0.65}
        if val < -0.1: return {"action": "SELL", "score": 0.35}
        return {"action": "HOLD", "score": 0.5}

    @staticmethod
    def donchian_breakout(df: pd.DataFrame, period: int = 20) -> Dict[str, Any]:
        upper = df['high'].rolling(period).max().shift(1)
        lower = df['low'].rolling(period).min().shift(1)
        curr = df['close'].iloc[-1]
        if curr > upper.iloc[-1]: return {"action": "BUY", "score": 0.85}
        if curr < lower.iloc[-1]: return {"action": "SELL", "score": 0.15}
        return {"action": "HOLD", "score": 0.5}

    @staticmethod
    def stochastic_rsi(df: pd.DataFrame, period: int = 14) -> Dict[str, Any]:
        from core.utils import compute_rsi
        rsi = compute_rsi(df['close'], period)
        stoch_rsi = (rsi - rsi.rolling(period).min()) / (rsi.rolling(period).max() - rsi.rolling(period).min() + 1e-9)
        val = stoch_rsi.iloc[-1]
        if val < 0.2: return {"action": "BUY", "score": 0.75}
        if val > 0.8: return {"action": "SELL", "score": 0.25}
        return {"action": "HOLD", "score": 0.5}

    @staticmethod
    def tema(df: pd.DataFrame, period: int = 20) -> Dict[str, Any]:
        c = df['close']
        ema1 = c.ewm(span=period).mean()
        ema2 = ema1.ewm(span=period).mean()
        ema3 = ema2.ewm(span=period).mean()
        tema_val = 3 * ema1 - 3 * ema2 + ema3
        if c.iloc[-1] > tema_val.iloc[-1]: return {"action": "BUY", "score": 0.65}
        return {"action": "SELL", "score": 0.35}

    @staticmethod
    def heikin_ashi(df: pd.DataFrame) -> Dict[str, Any]:
        h_close = (df['open'] + df['high'] + df['low'] + df['close']) / 4
        h_open = (df['open'].shift(1) + df['close'].shift(1)) / 2
        if h_close.iloc[-1] > h_open.iloc[-1]: return {"action": "BUY", "score": 0.6}
        return {"action": "SELL", "score": 0.4}

    @staticmethod
    def bull_bear_power(df: pd.DataFrame, period: int = 13) -> Dict[str, Any]:
        ema = df['close'].ewm(span=period).mean()
        bull_p = df['high'] - ema
        bear_p = df['low'] - ema
        if bull_p.iloc[-1] > 0 and bear_p.iloc[-1] > 0: return {"action": "BUY", "score": 0.7}
        if bull_p.iloc[-1] < 0 and bear_p.iloc[-1] < 0: return {"action": "SELL", "score": 0.3}
        return {"action": "HOLD", "score": 0.5}

    @staticmethod
    def mfi(df: pd.DataFrame, period: int = 14) -> Dict[str, Any]:
        tp = (df['high'] + df['low'] + df['close']) / 3
        rmf = tp * df['volume']
        # Simplified MFI approx
        if rmf.iloc[-1] > rmf.iloc[-2]: return {"action": "BUY", "score": 0.6}
        return {"action": "SELL", "score": 0.4}

    @staticmethod
    def vwap_reversion(df: pd.DataFrame) -> Dict[str, Any]:
        from core.utils import compute_vwap
        vwap = compute_vwap(df)
        curr = df['close'].iloc[-1]
        
        dist_pct = (curr - vwap) / vwap
        if dist_pct < -0.02: return {"action": "BUY", "score": 0.8} # Stretched down
        if dist_pct > 0.02: return {"action": "SELL", "score": 0.2} # Stretched up
        return {"action": "HOLD", "score": 0.5}

    @staticmethod
    def adx_trend(df: pd.DataFrame) -> Dict[str, Any]:
        from core.utils import compute_adx
        adx = compute_adx(df)
        if adx.iloc[-1] > 25:
            # Strong trend, use EMA cross for direction
            c = df['close']
            if c.iloc[-1] > c.rolling(50).mean().iloc[-1]:
                return {"action": "BUY", "score": 0.8}
            else:
                return {"action": "SELL", "score": 0.2}
        return {"action": "HOLD", "score": 0.5}
