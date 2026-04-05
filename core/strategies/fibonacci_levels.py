import pandas as pd
import numpy as np
from typing import Dict, Any

def calculate_swing_points(df: pd.DataFrame, window: int = 50) -> Dict[str, float]:
    """
    Find major swing high and swing low in a given period for Fibonacci drawing.
    """
    if df is None or len(df) < window:
        return {"high": 0.0, "low": 0.0}
        
    recent = df.tail(window)
    return {
        "high": float(recent['high'].max()),
        "low": float(recent['low'].min()),
        "timestamp_high": int(recent[recent['high'] == recent['high'].max()]['timestamp'].iloc[-1]),
        "timestamp_low": int(recent[recent['low'] == recent['low'].min()]['timestamp'].iloc[-1])
    }

def get_fib_retracements(swing_low: float, swing_high: float) -> Dict[str, float]:
    """
    Standard Fibonacci retracement levels for trading.
    """
    diff = swing_high - swing_low
    if diff == 0: return {}
    
    levels = {
        "0.236": swing_high - (diff * 0.236),
        "0.382": swing_high - (diff * 0.382),
        "0.5":   swing_high - (diff * 0.5), # Psychological level
        "0.618": swing_high - (diff * 0.618), # Golden Pocket start
        "0.786": swing_high - (diff * 0.786), # Deep retrace
        "1.0":   swing_low
    }
    
    return {k: round(v, 8) for k, v in levels.items()}

def get_confluence_zone(price: float, fibs: Dict[str, float], tolerance: float = 0.005) -> Dict[str, Any]:
    """
    Checks if a price is near any major Fibonacci level.
    """
    for level, val in fibs.items():
        if abs(price - val) / val <= tolerance:
            return {"level": level, "value": val, "hit": True}
    return {"level": None, "value": 0, "hit": False}
