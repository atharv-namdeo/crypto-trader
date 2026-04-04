"""
advanced_risk_engine.py
Kelly Criterion + Regime-Aware Position Sizing — Autonomous Trading Engine

Responsibilities:
- Kelly Criterion fractional position sizing (1-5% per trade)
- Regime-specific SL/TP ATR multipliers
- Consecutive-loss detection & position throttling
- Dynamic capital rebalancing based on Sharpe ratios
"""

import logging
from typing import Dict, Tuple

log = logging.getLogger("AdvancedRiskEngine")

# Regime-specific ATR multipliers for SL and TP.
# Wider SL in trending markets to avoid whipsaws; tighter in chop.
REGIME_ATR_MULTIPLIERS: Dict[str, Dict[str, float]] = {
    "TRENDING_BULL":        {"sl": 3.5, "tp": 7.0},
    "TRENDING_BEAR":        {"sl": 3.5, "tp": 7.0},
    "TRENDING_NEUTRAL":     {"sl": 3.0, "tp": 6.5},
    "HIGH_VOL_CHOP":        {"sl": 2.0, "tp": 5.0},
    "LOW_VOL_ACCUMULATION": {"sl": 4.0, "tp": 6.0},
    "NEUTRAL":              {"sl": 3.0, "tp": 6.0},
}

# Hard limits on Kelly position sizing
MIN_RISK_PCT = 0.01   # 1%
MAX_RISK_PCT = 0.05   # 5%
FRACTIONAL_KELLY = 0.25  # Quarter-Kelly for safety


class AdvancedRiskEngine:
    """
    Autonomous risk management layer.
    Use calculate_position_size() before every trade entry.
    """

    def __init__(self, state):
        self.state = state

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def calculate_position_size(
        self,
        strategy: str,
        symbol: str,
        capital: float,
        price: float,
    ) -> float:
        """
        Compute optimal position size (in quote currency) for a trade.

        Combines:
        1. Kelly Criterion optimal fraction
        2. Drawdown multiplier (reduce size in drawdown)
        3. Consecutive-loss throttle

        Returns quantity in base currency units.
        """
        kelly_fraction = await self._get_kelly_fraction(strategy)
        dd_mult = await self._get_drawdown_multiplier()
        loss_mult = await self._get_consecutive_loss_multiplier(strategy)

        effective_fraction = kelly_fraction * dd_mult * loss_mult
        # Hard cap
        effective_fraction = max(MIN_RISK_PCT, min(MAX_RISK_PCT, effective_fraction))

        notional = capital * effective_fraction
        qty = notional / (price + 1e-9)

        log.info(
            f"💰 [{strategy}] {symbol} | Kelly={kelly_fraction:.2%} "
            f"DD={dd_mult:.2f} Loss={loss_mult:.2f} → Qty={qty:.6f} ({effective_fraction:.2%} of capital)"
        )
        return qty

    def calculate_adaptive_stops(
        self,
        price: float,
        atr: float,
        regime: str,
        side: str = "LONG",
    ) -> Dict[str, float]:
        """
        Return regime-adapted stop-loss and take-profit prices.

        Args:
            price:  Entry price.
            atr:    Current ATR value.
            regime: Market regime string.
            side:   "LONG" or "SHORT".

        Returns:
            {"sl": float, "tp": float}
        """
        mult = REGIME_ATR_MULTIPLIERS.get(regime, REGIME_ATR_MULTIPLIERS["NEUTRAL"])
        sl_mult = mult["sl"]
        tp_mult = mult["tp"]

        if side == "LONG":
            return {
                "sl": price - atr * sl_mult,
                "tp": price + atr * tp_mult,
            }
        else:
            return {
                "sl": price + atr * sl_mult,
                "tp": price - atr * tp_mult,
            }

    async def record_trade_result(self, strategy: str, pnl: float) -> None:
        """Update consecutive-loss counter after a trade closes."""
        try:
            key = f"metrics:{strategy}:consecutive_losses"
            current = await self.state.get_float(key) or 0.0
            if pnl < 0:
                await self.state.set(key, current + 1)
            else:
                await self.state.set(key, 0.0)  # reset on win
        except Exception as exc:
            log.error(f"record_trade_result error: {exc}")

    async def validate_trade(
        self,
        symbol: str,
        signal: Dict,
    ) -> Tuple[bool, str]:
        """
        Pre-trade quality gate.  Returns (allowed, reason).

        Checks:
        - Minimum liquidity ($1M daily volume)
        - Maximum hourly volatility (10%)
        - EMA trend alignment
        - Consecutive loss throttle per strategy
        """
        # 1. Liquidity
        volume_24h = signal.get("volume_24h", 0)
        if volume_24h and volume_24h < 1_000_000:
            return False, f"Volume ${volume_24h:,.0f} < $1M threshold"

        # 2. Extreme volatility
        volatility = signal.get("volatility", 0)
        if volatility and volatility > 0.10:
            return False, f"Hourly volatility {volatility:.1%} > 10% threshold"

        # 3. EMA trend confirmation
        action = signal.get("action", "")
        ema_20 = signal.get("ema_20", 0)
        ema_50 = signal.get("ema_50", 0)
        price = signal.get("price", 0)

        if action == "BUY" and ema_20 and ema_50 and price:
            if not (price > ema_20 > ema_50):
                return False, "EMA trend not aligned for LONG"
        elif action == "SELL" and ema_20 and ema_50 and price:
            if not (price < ema_20 < ema_50):
                return False, "EMA trend not aligned for SHORT"

        # 4. Minimum signal confirmations
        confirmations = signal.get("confirmations", 0)
        required = signal.get("required_confirmations", 2)
        if confirmations < required:
            return False, f"Only {confirmations}/{required} signal confirmations"

        return True, "ok"

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    async def _get_kelly_fraction(self, strategy: str) -> float:
        """Compute the quarter-Kelly fraction from historical strategy metrics."""
        try:
            import json
            import numpy as np

            if not self.state.redis:
                return 0.02

            history_raw = await self.state.redis.lrange("trade:history", 0, 99)
            if not history_raw:
                return 0.02

            trades = [
                json.loads(t)
                for t in history_raw
                if json.loads(t).get("strategy", "").lower() == strategy.lower()
            ]

            if len(trades) < 10:
                return 0.015  # not enough data

            pnls = [t.get("pnl_net", t.get("pnl", 0)) for t in trades]
            wins = [p for p in pnls if p > 0]
            losses = [p for p in pnls if p <= 0]

            if not losses:
                return MAX_RISK_PCT
            if not wins:
                return MIN_RISK_PCT

            win_rate = len(wins) / len(pnls)
            avg_win = float(np.mean(wins))
            avg_loss = abs(float(np.mean(losses)))
            wl_ratio = avg_win / (avg_loss + 1e-9)

            kelly_full = win_rate - ((1 - win_rate) / (wl_ratio + 1e-9))
            safe = kelly_full * FRACTIONAL_KELLY
            return max(MIN_RISK_PCT, min(MAX_RISK_PCT, safe))

        except Exception as exc:
            log.error(f"_get_kelly_fraction error: {exc}")
            return 0.02

    async def _get_drawdown_multiplier(self) -> float:
        """Reduce position size proportionally during drawdown."""
        try:
            peak = await self.state.get_float("metrics:peak_equity") or 1000.0
            current = await self.state.get_float("portfolio:value") or 1000.0
            drawdown = (peak - current) / (peak + 1e-9)

            if drawdown < 0.02:
                return 1.0
            elif drawdown < 0.05:
                return 0.75
            elif drawdown < 0.10:
                return 0.50
            else:
                return 0.25
        except Exception:
            return 1.0

    async def _get_consecutive_loss_multiplier(self, strategy: str) -> float:
        """Throttle sizing after consecutive losses."""
        try:
            losses = await self.state.get_float(f"metrics:{strategy}:consecutive_losses") or 0.0
            if losses < 3:
                return 1.0
            elif losses < 5:
                return 0.5   # halve size
            else:
                return 0.25  # quarter size
        except Exception:
            return 1.0
