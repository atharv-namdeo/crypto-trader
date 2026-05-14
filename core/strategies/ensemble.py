"""
core/strategies/ensemble_algorithm.py  — PHASE 11 "OMEGA BRAIN"

Changes vs Phase 10:
  1. Integrated "Adaptive Omega Brain": Real-time condition-wise weight shifting.
  2. Asset Profiling: Custom weights for Trend-Followers (DOGE/SOL) vs Range-Bound (LINK/ADA).
  3. State Detection: Trending, Ranging, Expansion, and Compression states.
  4. Volatility Scaling: Dynamic VCE weighting during compression phases.
  5. Trend Strength Filter: ADX-based activation for MDT and Pulse engines.

Disabled strategies (kept as comments for future re-activation):
  MTF, STAT_ARB, BREAKOUT, OBIS, VWAP_REVERSION, LIQUIDITY_SWEEP,
  FIBONACCI, ICHIMOKU, ATR_EXPANSION, VOLUME_PROFILE, PIVOT_POINTS,
  PSAR, SUPERTREND, GANN_FAN, HARMONIC, LIQUIDITY_GRAB,
  TREND_EXHAUSTION, MTF_MACD, RSI_DIV
"""

import logging
import pandas as pd
import numpy as np
from datetime import datetime
import asyncio
from typing import Dict, Any

from core.strategies.price_action import (
    calculate_swing_points, get_fib_retracements, ZoneTradeFilter,
    PriceActionZoneEngine,
)
from core.strategies.regime import AdvancedRegimeDetector, MarketPhase

# Strategy Library Imports
from core.strategies.library.momentum_trend import MomentumStrategy
from core.strategies.library.rsi_reversion import RSIReversionStrategy
from core.strategies.library.vce_coil import VCEStrategy
from core.strategies.library.mdt_trail import MDTStrategy
from core.strategies.library.pee_pulse import PEEStrategy

log = logging.getLogger("EnsembleAlgorithm")


class EnsembleAlgorithm:
    """
    PHASE 11 — Adaptive Omega Brain (Condition-Wise Strategy Selection).
    Dynamic weighting based on Market State (Trend/Range/Vol) and Asset Profile.
    Institutional-grade execution with 5-strategy adaptive ensemble.
    """

    def __init__(self, state_manager):
        self.state           = state_manager
        self.zone_engine     = PriceActionZoneEngine()
        self.regime_detector = AdvancedRegimeDetector()
        self.phase           = MarketPhase

    # ── Main signal entry point ──────────────────────────────────────────────

    async def generate_signal(self, symbol: str) -> Dict[str, Any]:
        try:
            # 1. Fetch OHLCV data
            ohlcv_1d = await self.state.get_df(f"ohlcv:1d:{symbol}", n=250)
            ohlcv_1h = await self.state.get_df(f"ohlcv:1h:{symbol}", n=200)
            ohlcv_1m = await self.state.get_df(f"ohlcv:1m:{symbol}", n=100)

            if ohlcv_1d is None or ohlcv_1h is None:
                return self._neutral("Data gap")

            # Use 1h if 1m is missing (backtest mode)
            if ohlcv_1m is None:
                ohlcv_1m = ohlcv_1h.tail(100).copy()

            # 2. Regime classification (3-state EMA200)
            phase     = self.regime_detector.classify_market(ohlcv_1h)
            mult      = self.regime_detector.get_risk_multiplier(phase)

            # 4. Strategy signals (Computed from Library)
            momentum_sig = MomentumStrategy.generate(ohlcv_1h)
            rsi_sig      = RSIReversionStrategy.generate(ohlcv_1h, phase)
            vce_sig      = await VCEStrategy.generate(symbol, ohlcv_1h, self.state)
            mdt_sig      = MDTStrategy.generate(ohlcv_1h)
            pulse_sig    = PEEStrategy.generate(ohlcv_1h)

            # Early return for NEUTRAL / UNKNOWN (with full vote transparency)
            if phase in (MarketPhase.NEUTRAL, MarketPhase.UNKNOWN):
                buy_votes  = sum([momentum_sig["action"] == "BUY", rsi_sig["action"] == "BUY", vce_sig["action"] == "BUY", mdt_sig["action"] == "BUY", pulse_sig["action"] == "BUY"])
                sell_votes = sum([momentum_sig["action"] == "SELL", rsi_sig["action"] == "SELL", vce_sig["action"] == "SELL", mdt_sig["action"] == "SELL", pulse_sig["action"] == "SELL"])
                
                # Dynamic weights for reporting
                state   = self._identify_market_state(ohlcv_1h)
                profile = self._get_asset_profile(symbol)
                weights = self._get_adaptive_weights(state, profile, phase)

                return self._neutral(
                    f"[{state}] B:{buy_votes} S:{sell_votes} | W:M:{weights['MOM']:.1f} V:{weights['VCE']:.1f} T:{weights['MDT']:.1f}",
                    votes=(buy_votes, sell_votes)
                )

            # 3. Zone + Fib structure (for confirmation)
            zones  = self.zone_engine.find_major_zones(ohlcv_1d)
            swings = calculate_swing_points(ohlcv_1d, window=30)
            fibs   = get_fib_retracements(swings["low"], swings["high"])
            price  = float(ohlcv_1m["close"].iloc[-1])

            # 6. Adaptive Omega Brain (Dynamic Weighting)
            state   = self._identify_market_state(ohlcv_1h)
            profile = self._get_asset_profile(symbol)
            weights = self._get_adaptive_weights(state, profile, phase)

            base_score = (
                momentum_sig["score"] * weights["MOM"] +
                rsi_sig["score"]      * weights["RSI"] +
                vce_sig["score"]      * weights["VCE"] +
                mdt_sig["score"]      * weights["MDT"] +
                pulse_sig["score"]    * weights["PEE"]
            )

            # 7. Zone / pullback confirmation
            z_filter     = ZoneTradeFilter(self.zone_engine)
            valid_b, _   = z_filter.validate_entry("BUY",  price, zones, fibs)
            valid_s, _   = z_filter.validate_entry("SELL", price, zones, fibs)

            # EMA20/EMA50 pullback fallback
            ema20 = float(ohlcv_1h["close"].ewm(span=20, adjust=False).mean().iloc[-1])
            ema50 = float(ohlcv_1h["close"].ewm(span=50, adjust=False).mean().iloc[-1])
            pull_b = ZoneTradeFilter.entry_confirmed(price, ema20, ema50, "BUY")
            pull_s = ZoneTradeFilter.entry_confirmed(price, ema20, ema50, "SELL")

            # Either zone proximity OR pullback confirmation is sufficient
            confirmed_b = valid_b or pull_b
            confirmed_s = valid_s or pull_s

            # 8. Action decision
            action = "NEUTRAL"

            # Votes from all 5 strategies
            buy_votes  = sum([
                momentum_sig["action"] == "BUY", 
                rsi_sig["action"] == "BUY",
                vce_sig["action"] == "BUY",
                mdt_sig["action"] == "BUY",
                pulse_sig["action"] == "BUY"
            ])
            sell_votes = sum([
                momentum_sig["action"] == "SELL", 
                rsi_sig["action"] == "SELL",
                vce_sig["action"] == "SELL",
                mdt_sig["action"] == "SELL",
                pulse_sig["action"] == "SELL"
            ])

            if phase == MarketPhase.BULL:
                # Phase 9.5: Balanced selectivity
                if base_score >= 0.65 and buy_votes >= 1 and confirmed_b:
                    action = "BUY"

            elif phase == MarketPhase.BEAR:
                # Phase 9.5: Balanced selectivity
                if (1 - base_score) >= 0.65 and sell_votes >= 1 and confirmed_s:
                    action = "SELL"

            # 9. Macro conflict check (BTC EMA200 filter)
            if symbol == "BTC/USDT":
                btc_ohlcv_1h = ohlcv_1h
                btc_price    = price
            else:
                btc_ohlcv_1h = await self.state.get_df("ohlcv:1h:BTC/USDT", n=200)
                if btc_ohlcv_1h is not None:
                    btc_price = float(btc_ohlcv_1h["close"].iloc[-1])
                else:
                    btc_price = price # fallback

            btc_ema200 = self.regime_detector.compute_ema200(btc_ohlcv_1h)
            
            allowed, reason = AdvancedRegimeDetector.macro_conflict_check(
                action if action in ("BUY", "SELL") else "BUY",
                btc_price,
                btc_ema200,
            )
            if action in ("BUY", "SELL") and not allowed:
                log.info(f"[{symbol}] Macro conflict gate: {reason}")
                action = "NEUTRAL"

            # 10. ATR for sizing
            atr_val = self._calculate_atr(ohlcv_1h)
            rsi_1h  = self._calculate_rsi(ohlcv_1h["close"].values)

            payload = {
                "symbol":       symbol,
                "action":       action,
                "confidence":   float(base_score),
                "regime":       phase.value,
                "multiplier":   mult,
                "atr":          float(atr_val),
                "rsi":          float(rsi_1h),
                "ema20":        ema20,
                "ema50":        ema50,
                "buy_votes":    buy_votes,
                "sell_votes":   sell_votes,
                "confirmed_b":  confirmed_b,
                "confirmed_s":  confirmed_s,
                "timestamp":    int(datetime.utcnow().timestamp() * 1000),
                "reason": (
                    f"[{state}] Score:{base_score:.2f} "
                    f"Weights: M:{weights['MOM']:.1f} R:{weights['RSI']:.1f} V:{weights['VCE']:.1f} T:{weights['MDT']:.1f} P:{weights['PEE']:.1f} "
                    f"VCE:{vce_sig['action']} MDT:{mdt_sig['action']} PEE:{pulse_sig['action']}"
                ),
            }

            self.state.firebase.set(f"trading/signals/{symbol}", payload)
            return payload

        except Exception as e:
            log.error(f"Signal error for {symbol}: {e}")
            return self._neutral(str(e))

    # ── DISABLED STRATEGIES (Phase 8 and earlier) ───────────────────────────
    # Uncomment individually ONLY after proving base system is profitable live.
    #
    # def _mtf_signal(self, ...): ...           # MTF_MACD
    # def _stat_arb(self, ...): ...             # STAT_ARB
    # def _breakout(self, ...): ...             # BREAKOUT
    # def _obis(self, ...): ...                 # Order Book Imbalance
    # def _vwap_reversion(self, ...): ...       # VWAP_REVERSION
    # def _liquidity_sweep(self, ...): ...      # LIQUIDITY_SWEEP
    # def _fibonacci(self, ...): ...            # FIBONACCI
    # def _ichimoku(self, ...): ...             # ICHIMOKU
    # def _atr_expansion(self, ...): ...        # ATR_EXPANSION
    # def _volume_profile(self, ...): ...       # VOLUME_PROFILE
    # def _pivot_points(self, ...): ...         # PIVOT_POINTS
    # def _psar(self, ...): ...                 # PSAR
    # def _supertrend(self, ...): ...           # SUPERTREND
    # def _gann_fan(self, ...): ...             # GANN_FAN
    # def _harmonic(self, ...): ...             # HARMONIC
    # def _liquidity_grab(self, ...): ...       # LIQUIDITY_GRAB
    # def _trend_exhaustion(self, ...): ...     # TREND_EXHAUSTION
    # def _rsi_divergence(self, ...): ...       # RSI_DIV

    # ── Shared Indicators ───────────────────────────────────────────────────

    def _calculate_atr(self, df: pd.DataFrame, period: int = 14) -> float:
        if df is None or len(df) < period:
            return 0.01
        h, l, c = df["high"], df["low"], df["close"]
        tr = pd.concat([
            h - l,
            (h - c.shift()).abs(),
            (l - c.shift()).abs(),
        ], axis=1).max(axis=1)
        val = tr.rolling(period).mean().iloc[-1]
        return float(val) if not np.isnan(val) else 0.01

    def _calculate_rsi(self, prices, period: int = 14) -> float:
        if len(prices) < period:
            return 50.0
        deltas = np.diff(prices)
        up     = deltas[deltas > 0].sum()
        down   = -deltas[deltas < 0].sum()
        if down == 0:
            return 100.0
        rs = up / (down + 1e-9)
        return float(100 - (100 / (1 + rs)))

    # ── Helpers ─────────────────────────────────────────────────────────────

    @staticmethod
    def _neutral(reason: str = "", votes=(0,0)) -> Dict[str, Any]:
        return {
            "action":     "HOLD",
            "confidence": 0.5,
            "regime":     "NEUTRAL",
            "atr":        0.0,
            "rsi":        50.0,
            "buy_votes":  votes[0],
            "sell_votes": votes[1],
            "reason":     reason,
        }

    # ── Omega Brain Decision Logic ──────────────────────────────────────────

    def _identify_market_state(self, df: pd.DataFrame) -> str:
        """Categorizes market into Trending, Ranging, Expansion, or Compression."""
        if len(df) < 30: return "UNKNOWN"
        
        # 1. Volatility Ratio
        bg_atr    = self._calculate_atr(df, period=20)
        local_atr = self._calculate_atr(df, period=4)
        vol_ratio = local_atr / bg_atr if bg_atr > 0 else 1.0
        
        # 2. Trend Strength (Simplified ADX approx)
        closes = df["close"]
        ema20  = closes.ewm(span=20, adjust=False).mean()
        slope  = (ema20.iloc[-1] - ema20.iloc[-5]) / ema20.iloc[-5]
        
        if vol_ratio < 0.80: return "COMPRESSION"
        if vol_ratio > 1.40: return "EXPANSION"
        if abs(slope) > 0.0015: return "TRENDING"
        return "RANGING"

    def _get_asset_profile(self, symbol: str) -> str:
        """Determines behavioral profile based on 2-year audit results."""
        trend_followers = ["DOGE/USDT", "SOL/USDT", "AVAX/USDT", "SHIB/USDT"]
        range_bound     = ["LINK/USDT", "XRP/USDT", "ADA/USDT"]
        
        if symbol in trend_followers: return "TRENDER"
        if symbol in range_bound:     return "RANGER"
        return "MACRO"

    def _get_adaptive_weights(self, state: str, profile: str, phase: MarketPhase) -> Dict[str, float]:
        """The core decision matrix. Allocates weights based on all conditions."""
        # Default (Phase 10)
        weights = {"MOM": 0.3, "RSI": 0.2, "VCE": 0.2, "MDT": 0.15, "PEE": 0.15}
        
        # Condition 1: Neutral Regime (Choppy)
        if phase == MarketPhase.NEUTRAL:
            return {"MOM": 0.1, "RSI": 0.4, "VCE": 0.5, "MDT": 0.0, "PEE": 0.0}
            
        # Condition 2: High Compression (Wait for VCE breakout)
        if state == "COMPRESSION":
            return {"MOM": 0.1, "RSI": 0.1, "VCE": 0.8, "MDT": 0.0, "PEE": 0.0}
            
        # Condition 3: Strong Expansion (Ride the MDT trail)
        if state == "EXPANSION":
            return {"MOM": 0.2, "RSI": 0.0, "VCE": 0.0, "MDT": 0.5, "PEE": 0.3}
            
        # Condition 4: Asset Specific Bias
        if profile == "TRENDER" and state == "TRENDING":
            weights = {"MOM": 0.2, "RSI": 0.1, "VCE": 0.1, "MDT": 0.3, "PEE": 0.3}
        elif profile == "RANGER":
            weights = {"MOM": 0.2, "RSI": 0.4, "VCE": 0.4, "MDT": 0.0, "PEE": 0.0}
            
        return weights
