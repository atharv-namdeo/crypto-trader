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

def compute_vwap(df: pd.DataFrame) -> pd.Series:
    """Rolling VWAP over the available window."""
    typical_price = (df['high'] + df['low'] + df['close']) / 3
    volume = df['volume']
    vwap = (typical_price * volume).rolling(window=len(df), min_periods=1).sum() / volume.rolling(window=len(df), min_periods=1).sum()
    return vwap

def compute_atr(df: pd.DataFrame, period: int = 14) -> pd.Series:
    high, low, close = df['high'], df['low'], df['close']
    tr = pd.concat([
        high - low,
        (high - close.shift()).abs(),
        (low - close.shift()).abs()
    ], axis=1).max(axis=1)
    return tr.rolling(period).mean()
