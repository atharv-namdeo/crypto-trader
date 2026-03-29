import logging
import pandas as pd
import numpy as np
from datetime import datetime
import asyncio
from typing import Dict, Any

log = logging.getLogger("EnsembleAlgorithm")

class EnsembleAlgorithm:
    """
    Hedge Fund-grade Multi-Timeframe Trading Algorithm.
    Combines Short-term (1m), Medium-term (1h/4h), and Long-term (1d) signals.
    """
    
    def __init__(self, state_manager):
        self.state = state_manager
        
    async def generate_signal(self, symbol: str) -> Dict[str, Any]:
        """
        Generate a unified ensemble signal for a symbol.
        """
        try:
            # 1. Fetch Data for all timeframes
            ohlcv_1m = await self.state.get_df(f"ohlcv:1m:{symbol}", n=100)
            ohlcv_1h = await self.state.get_df(f"ohlcv:1h:{symbol}", n=100)
            ohlcv_4h = await self.state.get_df(f"ohlcv:4h:{symbol}", n=100)
            ohlcv_1d = await self.state.get_df(f"ohlcv:1d:{symbol}", n=200)
            
            if ohlcv_1m is None or ohlcv_1h is None:
                return {"action": "HOLD", "confidence": 0, "reason": "Insufficient data"}

            # 2. SHORT-TERM (30% weight) - Scalping / Mean Reversion
            short_signal = self._compute_short_term(ohlcv_1m)
            
            # 3. MEDIUM-TERM (35% weight) - Swing / ML
            # In a real scenario, we'd call the ML model here. For now, we simulate the logic.
            ml_pred = await self.state.get(f"ml_signal:{symbol}") or {"signal": "NEUTRAL", "confidence": 0.5}
            medium_signal = self._compute_medium_term(ohlcv_1h, ohlcv_4h, ml_pred)
            
            # 4. LONG-TERM (35% weight) - Trend Following
            long_signal = self._compute_long_term(ohlcv_1d)
            
            # 5. ENSEMBLE VOTING
            ensemble_score = (
                short_signal['score'] * 0.30 +
                medium_signal['score'] * 0.35 +
                long_signal['score'] * 0.35
            )
            
            action = "NEUTRAL"
            if ensemble_score > 0.65: action = "BUY"
            elif ensemble_score < 0.35: action = "SELL"
            
            signal_payload = {
                "symbol": symbol,
                "action": action,
                "confidence": ensemble_score,
                "timestamp": int(datetime.utcnow().timestamp() * 1000),
                "components": {
                    "short": short_signal,
                    "medium": medium_signal,
                    "long": long_signal
                },
                "reason": f"S:{short_signal['action']} M:{medium_signal['action']} L:{long_signal['action']}"
            }
            
            # Record signal in Firebase for Dashboard
            self.state.firebase.set(f"trading/signals/{symbol}", signal_payload)
            
            return signal_payload

        except Exception as e:
            log.error(f"Error generating ensemble signal for {symbol}: {e}")
            return {"action": "HOLD", "confidence": 0, "reason": str(e)}

    def _compute_short_term(self, df: pd.DataFrame) -> Dict[str, Any]:
        """1m Scalping logic: RSI + BB + ATR"""
        closes = df['close'].values
        rsi = self._calculate_rsi(closes)
        bb_upper, bb_lower = self._calculate_bb(closes)
        
        score = 0.5
        if rsi < 30 and closes[-1] < bb_lower: score = 0.8 # Oversold
        elif rsi > 70 and closes[-1] > bb_upper: score = 0.2 # Overbought
        
        return {
            "action": "BUY" if score > 0.6 else "SELL" if score < 0.4 else "NEUTRAL",
            "score": score,
            "rsi": float(rsi),
            "bb_dist_pct": float((closes[-1] - bb_lower) / (bb_upper - bb_lower)) if bb_upper != bb_lower else 0.5
        }

    def _compute_medium_term(self, df_1h: pd.DataFrame, df_4h: pd.DataFrame, ml_pred: dict) -> Dict[str, Any]:
        """1h/4h Swing logic: MACD + ML"""
        macd_signal = self._calculate_macd(df_1h['close'].values)
        
        ml_score = 0.5
        if ml_pred['signal'] == 'BUY': ml_score = ml_pred.get('confidence', 0.6)
        elif ml_pred['signal'] == 'SELL': ml_score = 1 - ml_pred.get('confidence', 0.6)
        
        # Combine MACD and ML
        combined = (macd_signal + ml_score) / 2
        
        return {
            "action": "BUY" if combined > 0.6 else "SELL" if combined < 0.4 else "NEUTRAL",
            "score": combined,
            "ml_conf": ml_score,
            "macd": macd_signal
        }

    def _compute_long_term(self, df_1d: pd.DataFrame) -> Dict[str, Any]:
        """Daily Trend logic: SMA 50/200"""
        if df_1d is None or len(df_1d) < 200:
            return {"action": "NEUTRAL", "score": 0.5}
            
        sma_50 = df_1d['close'].rolling(50).mean().iloc[-1]
        sma_200 = df_1d['close'].rolling(200).mean().iloc[-1]
        
        score = 0.8 if sma_50 > sma_200 else 0.2
        return {
            "action": "BUY" if score > 0.5 else "SELL",
            "score": score,
            "golden_cross": bool(sma_50 > sma_200)
        }

    # --- Indicators ---
    def _calculate_rsi(self, prices, period=14):
        if len(prices) < period: return 50
        deltas = np.diff(prices)
        up = deltas[deltas > 0].sum()
        down = -deltas[deltas < 0].sum()
        if down == 0: return 100
        rs = up / down
        return 100 - (100 / (1 + rs))

    def _calculate_bb(self, prices, period=20):
        if len(prices) < period: return prices[-1], prices[-1]
        sma = np.mean(prices[-period:])
        std = np.std(prices[-period:])
        return sma + 2*std, sma - 2*std

    def _calculate_macd(self, prices):
        if len(prices) < 26: return 0.5
        # Simplified MACD logic
        ema_12 = pd.Series(prices).ewm(span=12).mean().iloc[-1]
        ema_26 = pd.Series(prices).ewm(span=26).mean().iloc[-1]
        return 0.8 if ema_12 > ema_26 else 0.2
