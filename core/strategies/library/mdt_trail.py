import pandas as pd
import numpy as np
from typing import Dict, Any

class MDTStrategy:
    """
    Mean Deviation Trail (MDT)
    Adaptive trend following using MAD (Mean Absolute Deviation).
    """
    @staticmethod
    def generate(df: pd.DataFrame) -> Dict[str, Any]:
        if df is None or len(df) < 40:
            return {"action": "NEUTRAL", "score": 0.5}

        closes = df["close"]
        ema30  = closes.ewm(span=30, adjust=False).mean()
        
        # MAD Calculation
        mad_val = (closes - ema30).abs().rolling(9).mean().iloc[-1]
        
        if mad_val == 0: return {"action": "NEUTRAL", "score": 0.5}
        
        # Normalized Deviation
        dev_ema = (closes - ema30) / (closes - ema30).abs().rolling(9).mean()
        dev_sig = dev_ema.ewm(span=14, adjust=False).mean().iloc[-1]
        
        if dev_sig > 0.5:
            return {"action": "BUY", "score": 0.65}
        elif dev_sig < -0.5:
            return {"action": "SELL", "score": 0.35}
            
        return {"action": "NEUTRAL", "score": 0.5}
