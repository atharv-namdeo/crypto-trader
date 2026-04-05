import logging
import pandas as pd
import numpy as np
from datetime import datetime
import asyncio
from typing import Dict, Any
from core.strategies.price_action_engine import calculate_swing_points, get_fib_retracements, ZoneTradeFilter

log = logging.getLogger("EnsembleAlgorithm")

class EnsembleAlgorithm:
    """
    Hedge Fund-grade Multi-Timeframe Trading Algorithm.
    Combines Short-term (1m), Medium-term (1h/4h), and Long-term (1d) signals.
    """
    
    def __init__(self, state_manager):
        self.state = state_manager
        from core.strategies.price_action_engine import PriceActionZoneEngine
        from core.strategies.regime_classifier import AdvancedRegimeDetector, MarketPhase
        self.zone_engine = PriceActionZoneEngine()
        self.regime_detector = AdvancedRegimeDetector()
        self.phase = MarketPhase
        
    async def generate_signal(self, symbol: str) -> Dict[str, Any]:
        """
        Generate a unified ensemble signal for a symbol.
        """
        try:
            # 1. Fetch Data
            # 1. Fetch Data (1d for zones, 1m/1h for signals)
            ohlcv_1d = await self.state.get_df(f"ohlcv:1d:{symbol}", n=200)
            ohlcv_1h = await self.state.get_df(f"ohlcv:1h:{symbol}", n=100)
            ohlcv_1m = await self.state.get_df(f"ohlcv:1m:{symbol}", n=100)
            
            if ohlcv_1d is None or ohlcv_1h is None:
                return {"action": "HOLD", "confidence": 0, "reason": "Data gap"}

            # 2. Structural Analysis (Zones & Fibs)
            zones = self.zone_engine.find_major_zones(ohlcv_1d)
            swings = calculate_swing_points(ohlcv_1d, window=30)
            fibs = get_fib_retracements(swings['low'], swings['high'])
            
            # 3. Regime Classification (Advanced 10-Phase)
            best_df = ohlcv_1h if len(ohlcv_1h) >= 50 else ohlcv_1d
            phase = self.regime_detector.classify_market(best_df)
            mult = self.regime_detector.get_risk_multiplier(phase)

            # 4. Core Signals
            short_signal = self._compute_short_term(ohlcv_1m)
            ml_pred = await self.state.get(f"ml_signal:{symbol}") or {"signal": "NEUTRAL", "confidence": 0.5}
            medium_signal = self._compute_medium_term(ohlcv_1h, None, ml_pred)
            long_signal = self._compute_long_term(ohlcv_1d)
            
            # 5. ENSEMBLE VOTING (Phase 8 Weights)
            base_score = (
                short_signal['score'] * 0.15 + 
                medium_signal['score'] * 0.45 +
                long_signal['score'] * 0.40
            )
            
            # Structural Alpha Boost (New Phase 8.5)
            # Find closest zone proximity
            price = ohlcv_1m['close'].iloc[-1]
            structural_bonus = 0.0
            z_filter = ZoneTradeFilter(self.zone_engine)
            valid_b, conf_b = z_filter.validate_entry('BUY', price, zones, fibs)
            valid_s, conf_s = z_filter.validate_entry('SELL', price, zones, fibs)
            
            if valid_b: structural_bonus = 0.05 # +5% confidence for structural alignment
            if valid_s: structural_bonus = -0.05 # subtract for sell
            
            ensemble_score = base_score + structural_bonus
            
            # 6. ACTION SELECTION with Structural Gating & MTF Quorum
            action = "NEUTRAL"
            
            # Use regime-specific confidence thresholds (Final Profit Optimized)
            required_confidence = 0.65 # Default Trend
            if phase.value in ["HIGH_VOL_CHOP"]:
                required_confidence = 0.80
            elif phase.value in ["LOW_VOL_ACCUMULATION", "ACCUMULATION"]:
                required_confidence = 0.75
            
            # Count Confirmation Votes (Need 2+ Agreement)
            buy_votes = sum([
                short_signal['action'] == 'BUY',
                medium_signal['action'] == 'BUY',
                long_signal['action'] == 'BUY'
            ])
            sell_votes = sum([
                short_signal['action'] == 'SELL',
                medium_signal['action'] == 'SELL',
                long_signal['action'] == 'SELL'
            ])
            
            # Apply Quorum + Structural Logic
            if ensemble_score >= required_confidence and buy_votes >= 2:
                if valid_b and phase not in [self.phase.CONSOLIDATION_WIDE, self.phase.MATURE_BEAR_DECLINE]:
                    action = "BUY"
            elif (1 - ensemble_score) >= required_confidence and sell_votes >= 2:
                if valid_s and phase in [self.phase.EARLY_BEAR_BREAKDOWN, self.phase.MATURE_BEAR_DECLINE, self.phase.DISTRIBUTION]:
                    action = "SELL"
            
            # 6.5 RSI Exhaustion Check (New Phase 8.5)
            # If RSI is extreme, suggest immediate profit taking
            rsi_1h = self._calculate_rsi(ohlcv_1h['close'].values)
            suggested_exit = False
            if (action == "BUY" and rsi_1h > 80) or (action == "SELL" and rsi_1h < 20):
                log.info(f"🔥 RSI EXHAUSTION for {symbol}: {rsi_1h:.1f}")
                suggested_exit = True
            
            # 7. Volatility for sizing
            atr_val = self._calculate_atr(ohlcv_1h)
            
            signal_payload = {
                "symbol": symbol,
                "action": action,
                "confidence": float(ensemble_score),
                "confirmations": int(max(buy_votes, sell_votes)),
                "multiplier": mult,
                "regime": phase.value,
                "atr": float(atr_val),
                "rsi": float(rsi_1h),
                "suggested_exit": suggested_exit,
                "timestamp": int(datetime.utcnow().timestamp() * 1000),
                "reason": f"Ph:{phase.value} Conf:{ensemble_score:.2f} Votes:{max(buy_votes, sell_votes)} RSI:{rsi_1h:.1f}"
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

    def _calculate_atr(self, df: pd.DataFrame, period=14):
        if df is None or len(df) < period: return 0.01 
        high, low, close = df['high'], df['low'], df['close']
        tr = pd.concat([high - low, (high - close.shift()).abs(), (low - close.shift()).abs()], axis=1).max(axis=1)
        return tr.rolling(period).mean().iloc[-1]

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
