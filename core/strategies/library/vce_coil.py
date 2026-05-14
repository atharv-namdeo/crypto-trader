import pandas as pd
from typing import Dict, Any

class VCEStrategy:
    """
    Volatility Coil Edge (VCE)
    Detects price compression at session extremes.
    """
    @staticmethod
    async def generate(symbol: str, df: pd.DataFrame, state_manager) -> Dict[str, Any]:
        if df is None or len(df) < 50:
            return {"action": "NEUTRAL", "score": 0.5}

        # 1. Metrics
        h, l, c = df["high"], df["low"], df["close"]
        tr = pd.concat([h - l, (h - c.shift()).abs(), (l - c.shift()).abs()], axis=1).max(axis=1)
        bg_atr    = tr.rolling(20).mean().iloc[-1]
        local_atr = tr.rolling(4).mean().iloc[-1]
        
        hi_50     = h.rolling(50).max().iloc[-1]
        lo_50     = l.rolling(50).min().iloc[-1]
        rng_50    = hi_50 - lo_50
        
        # 2. Compression check
        contracted = local_atr < (bg_atr * 0.82)
        
        # 3. Zone check
        price    = float(c.iloc[-1])
        zone_top = hi_50 - rng_50 * 0.35
        zone_bot = lo_50 + rng_50 * 0.35
        at_high  = price >= zone_top
        at_low   = price <= zone_bot
        
        # 4. State Management
        state_key = f"vce_state:{symbol}"
        v_state = await state_manager.get(state_key) or {"count": 0, "hi": 0, "lo": 0, "active": False}
        
        if contracted:
            if v_state["count"] == 0:
                v_state = {"count": 1, "hi": h.iloc[-1], "lo": l.iloc[-1], "active": True}
            else:
                v_state["count"] += 1
                v_state["hi"] = max(v_state["hi"], h.iloc[-1])
                v_state["lo"] = min(v_state["lo"], l.iloc[-1])
        else:
            v_state["count"] = max(0, v_state["count"] - 1)
            if v_state["count"] == 0: v_state["active"] = False

        await state_manager.set(state_key, v_state)
        
        # 5. Signal logic
        if v_state["count"] >= 4 and v_state["active"]:
            if at_high and price < v_state["lo"]:
                return {"action": "SELL", "score": 0.30, "reason": "vce_break_down"}
            if at_low and price > v_state["hi"]:
                return {"action": "BUY", "score": 0.70, "reason": "vce_break_up"}
                
        return {"action": "NEUTRAL", "score": 0.5}
