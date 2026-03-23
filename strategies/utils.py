import pandas as pd
import numpy as np

def compute_rsi(series: pd.Series, period: int = 14) -> pd.Series:
    delta = series.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))

def compute_adx(df: pd.DataFrame, period: int = 14) -> pd.Series:
    high, low, close = df['high'], df['low'], df['close']
    tr = pd.concat([
        high - low,
        (high - close.shift()).abs(),
        (low - close.shift()).abs()
    ], axis=1).max(axis=1)
    
    dm_plus  = ((high - high.shift()) > (low.shift() - low)).astype(float) * (high - high.shift()).clip(lower=0)
    dm_minus = ((low.shift() - low) > (high - high.shift())).astype(float) * (low.shift() - low).clip(lower=0)
    
    atr14     = tr.rolling(period).mean()
    di_plus   = 100 * dm_plus.rolling(period).mean() / atr14
    di_minus  = 100 * dm_minus.rolling(period).mean() / atr14
    dx        = 100 * (di_plus - di_minus).abs() / (di_plus + di_minus + 1e-9)
    adx       = dx.rolling(period).mean()
    return adx

def compute_vwap(df):
    typical_price = (df['high'] + df['low'] + df['close']) / 3
    cumulative_tp_vol = (typical_price * df['volume']).cumsum()
    cumulative_vol = df['volume'].cumsum()
    return (cumulative_tp_vol / cumulative_vol).iloc[-1]

def compute_atr(df: pd.DataFrame, period: int = 14) -> pd.Series:
    high, low, close = df['high'], df['low'], df['close']
    tr = pd.concat([
        high - low,
        (high - close.shift()).abs(),
        (low - close.shift()).abs()
    ], axis=1).max(axis=1)
    return tr.rolling(period).mean()

def compute_ultosc(df: pd.DataFrame, p1: int = 7, p2: int = 14, p3: int = 28) -> pd.Series:
    """Ultimate Oscillator"""
    low_diff = df['close'] - df['low']
    tp_diff = df['high'] - df['low']
    
    avg1 = low_diff.rolling(p1).sum() / (tp_diff.rolling(p1).sum() + 1e-9)
    avg2 = low_diff.rolling(p2).sum() / (tp_diff.rolling(p2).sum() + 1e-9)
    avg3 = low_diff.rolling(p3).sum() / (tp_diff.rolling(p3).sum() + 1e-9)
    
    return 100 * (4 * avg1 + 2 * avg2 + avg3) / 7
