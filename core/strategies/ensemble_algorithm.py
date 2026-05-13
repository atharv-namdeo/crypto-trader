"""
core/strategies/ensemble_algorithm.py  — PHASE 9 REBUILD

Changes vs Phase 8:
  1. ML signal neutralized (forced to 0.5) — no more lookahead leakage
  2. Short-term signal replaced with EMA9/EMA21 crossover (MOMENTUM_TREND)
  3. Medium-term signal is RSI_MEAN_REVERSION (RSI vs 35/65 thresholds)
  4. Long-term signal kept (SMA50 vs SMA200 golden/death cross)
  5. Regime gate is now 3-state BULL/BEAR/NEUTRAL from EMA200
  6. Macro conflict check (BTC deviation > 5%) blocks conflicting trades
  7. Zone proximity is now 2.5% + EMA pullback fallback confirmation
  8. All other strategies commented out (not deleted)

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

from core.strategies.price_action_engine import (
    calculate_swing_points, get_fib_retracements, ZoneTradeFilter,
    PriceActionZoneEngine,
)
from core.strategies.regime_classifier import AdvancedRegimeDetector, MarketPhase

log = logging.getLogger("EnsembleAlgorithm")


class EnsembleAlgorithm:
    """
    PHASE 9 — 2-strategy ensemble (MOMENTUM_TREND + RSI_MEAN_REVERSION).
    Regime-gated by 3-state EMA200 classifier.
    All ML signals neutralized.
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

            # Block everything in NEUTRAL / UNKNOWN
            if phase in (MarketPhase.NEUTRAL, MarketPhase.UNKNOWN):
                return self._neutral(f"Regime={phase.value} — no new trades")

            # 3. Zone + Fib structure (for confirmation)
            zones  = self.zone_engine.find_major_zones(ohlcv_1d)
            swings = calculate_swing_points(ohlcv_1d, window=30)
            fibs   = get_fib_retracements(swings["low"], swings["high"])
            price  = float(ohlcv_1m["close"].iloc[-1])

            # 4. Strategy signals
            #    MOMENTUM_TREND   — EMA9/EMA21 crossover + volume
            #    RSI_MEAN_REVERSION — RSI vs 35/65 in regime context
            momentum_sig = self._momentum_trend(ohlcv_1h)
            rsi_sig      = self._rsi_mean_reversion(ohlcv_1h, phase)

            # 5. ML signal  — NEUTRALIZED (Phase 9)
            # ml_pred = await self.state.get(f"ml_signal:{symbol}")  # DISABLED
            ml_signal_score = 0.5   # fixed neutral — do not change until walk-forward retrain

            # 6. Ensemble score (momentum 60%, RSI 40%, ML 0%)
            base_score = (
                momentum_sig["score"] * 0.60 +
                rsi_sig["score"]      * 0.40
                # ml_signal_score * 0.00   # intentionally zero
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

            # Votes from both strategies
            buy_votes  = sum([momentum_sig["action"] == "BUY",  rsi_sig["action"] == "BUY"])
            sell_votes = sum([momentum_sig["action"] == "SELL", rsi_sig["action"] == "SELL"])

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
                    f"Ph:{phase.value} Score:{base_score:.2f} "
                    f"Mom:{momentum_sig['action']} RSI:{rsi_sig['action']} "
                    f"ConfB:{confirmed_b} ConfS:{confirmed_s}"
                ),
            }

            self.state.firebase.set(f"trading/signals/{symbol}", payload)
            return payload

        except Exception as e:
            log.error(f"Signal error for {symbol}: {e}")
            return self._neutral(str(e))

    # ── Strategy 1: MOMENTUM TREND (EMA9/EMA21 crossover + volume) ──────────

    def _momentum_trend(self, df: pd.DataFrame) -> Dict[str, Any]:
        """
        BUY  when EMA9 crosses above EMA21 AND volume > 20-bar avg volume.
        SELL when EMA9 crosses below EMA21 AND volume > 20-bar avg volume.
        """
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

        # Trend direction even without fresh crossover
        bull_trend = ema9.iloc[-1] > ema21.iloc[-1]
        bear_trend = ema9.iloc[-1] < ema21.iloc[-1]

        if cross_up or (bull_trend and vol_ok):
            score = 0.75 if cross_up else 0.62
            return {"action": "BUY",  "score": score, "cross": cross_up}
        elif cross_down or (bear_trend and vol_ok):
            score = 0.25 if cross_down else 0.38
            return {"action": "SELL", "score": score, "cross": cross_down}

        return {"action": "NEUTRAL", "score": 0.5}

    # ── Strategy 2: RSI MEAN REVERSION ──────────────────────────────────────

    def _rsi_mean_reversion(self, df: pd.DataFrame, phase: MarketPhase) -> Dict[str, Any]:
        """
        BULL regime: BUY  when RSI(14) crosses back above 35 (oversold bounce).
        BEAR regime: SELL when RSI(14) crosses back below 65 (overbought fade).
        """
        if df is None or len(df) < 20:
            return {"action": "NEUTRAL", "score": 0.5}

        closes   = df["close"].values
        rsi_now  = self._calculate_rsi(closes)
        rsi_prev = self._calculate_rsi(closes[:-1])

        if phase == MarketPhase.BULL:
            # Bounce off oversold
            if rsi_prev < 35 and rsi_now >= 35:
                return {"action": "BUY", "score": 0.72, "rsi": rsi_now}
            if rsi_now < 45:
                return {"action": "BUY", "score": 0.60, "rsi": rsi_now}

        elif phase == MarketPhase.BEAR:
            # Fade overbought rally
            if rsi_prev > 65 and rsi_now <= 65:
                return {"action": "SELL", "score": 0.28, "rsi": rsi_now}
            if rsi_now > 55:
                return {"action": "SELL", "score": 0.40, "rsi": rsi_now}

        return {"action": "NEUTRAL", "score": 0.5, "rsi": rsi_now}

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
    def _neutral(reason: str = "") -> Dict[str, Any]:
        return {
            "action":     "HOLD",
            "confidence": 0.5,
            "regime":     "NEUTRAL",
            "atr":        0.0,
            "rsi":        50.0,
            "reason":     reason,
        }
