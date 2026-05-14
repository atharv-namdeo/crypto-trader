import pandas as pd
from typing import Dict, Any

class MomentumStrategy:
    """
    Momentum Trend Strategy
    EMA crossover with volume confirmation.
    """
    @staticmethod
    def generate(df: pd.DataFrame) -> Dict[str, Any]:
        if df is None or len(df) < 30:
            return {"action": "NEUTRAL", "score": 0.5}

        closes = df["close"]
        ema9   = closes.ewm(span=9,  adjust=False).mean()
        ema21  = closes.ewm(span=21, adjust=False).mean()

        cross_up   = (ema9.iloc[-1] > ema21.iloc[-1]) and (ema9.iloc[-2] <= ema21.iloc[-2])
        cross_down = (ema9.iloc[-1] < ema21.iloc[-1]) and (ema9.iloc[-2] >= ema21.iloc[-2])

        # Volume confirmation
        vol_ok = False
        if "volume" in df.columns and len(df) >= 20:
            avg_vol = df["volume"].iloc[-20:].mean()
            vol_ok  = float(df["volume"].iloc[-1]) > avg_vol

        bull_trend = ema9.iloc[-1] > ema21.iloc[-1]
        bear_trend = ema9.iloc[-1] < ema21.iloc[-1]

        if cross_up or (bull_trend and vol_ok):
            score = 0.75 if cross_up else 0.62
            return {"action": "BUY",  "score": score, "cross": cross_up}
        elif cross_down or (bear_trend and vol_ok):
            score = 0.25 if cross_down else 0.38
            return {"action": "SELL", "score": score, "cross": cross_down}

        return {"action": "NEUTRAL", "score": 0.5}
