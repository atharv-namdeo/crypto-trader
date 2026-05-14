"""
core/risk.py — PHASE 9 REBUILD

Changes vs Phase 8:
  1. Kelly criterion REMOVED — replaced with fixed 1% risk per trade
  2. Hard notional cap:  max 5% of capital at risk, max 30% notional
  3. Assertion raised if cap is ever breached before order submission
  4. Circuit breaker tightened:  daily DD 5% → 3%, weekly DD 8% added
  5. Weekly drawdown tracker persisted via daily_equity dict
  6. compute_position_size() is now synchronous (no Kelly async call needed)

Removed:
  - KellyCalculator dependency
  - Regime-based risk multiplier (regime gate is now in ensemble_algorithm.py)
  - All leverage references
"""

import logging
from datetime import datetime, timezone

log = logging.getLogger("RiskGuardian")


class RiskManager:
    """
    PHASE 9 — Hard-capped fixed-risk position sizing.
    No Kelly. No leverage. No exceptions.
    """

    # ── Hard limits ──────────────────────────────────────────────────────────
    MAX_PORTFOLIO_HEAT   = 0.10   # 10% total open risk
    MAX_ASSET_EXPOSURE   = 0.25   # 25% notional per asset (Phase 9.5)
    MAX_DAILY_DRAWDOWN   = 0.03   # 3% daily loss → halt    ← was 5%
    MAX_WEEKLY_DRAWDOWN  = 0.08   # 8% weekly loss → halt   ← NEW
    MIN_RR_RATIO         = 2.0    # 2:1 minimum reward/risk
    MAX_LEVERAGE         = 1.0    # no leverage              ← was 10×

    # ── Fixed sizing ─────────────────────────────────────────────────────────
    BASE_RISK_PCT        = 0.01   # risk 1% of capital per trade
    MAX_RISK_PCT         = 0.01   # same — no Kelly scaling
    MAX_NOTIONAL_PCT     = 0.25   # position never > 25% of capital (notional)
    MAX_SINGLE_RISK_PCT  = 0.05   # max 5% of capital at risk per trade

    def __init__(self, state=None):
        self.state       = state
        self.kelly       = None   # Kelly removed in Phase 9
        self.running     = False
        self._week_start_capital: float | None = None
        self._week_start_date:    str | None   = None

    # ── Position sizing (now synchronous) ────────────────────────────────────

    async def compute_position_size(
        self,
        capital: float,
        strategy: str  = "ENSEMBLE",
        atr:      float = 0.01,
        price:    float = 1.0,
        regime:   str   = "NEUTRAL",
        stop_atr_multiple: float = 1.8, # Phase 9.5: Balanced stops
    ) -> dict:
        """
        Fixed 1% risk sizing with hard notional and risk caps.

        Formula:
            risk_dollars   = capital × 1%
            stop_distance  = atr × 2.0
            stop_pct       = stop_distance / price
            position_value = risk_dollars / stop_pct

        Then capped at:
            min(position_value, capital × 5%)   — max risk cap
            min(position_value, capital × 30%)  — max notional cap
        """
        if price <= 0 or atr <= 0:
            return {"qty": 0.0, "notional": 0.0, "risk_pct": 0.0}

        risk_dollars   = capital * self.BASE_RISK_PCT          # 1% of capital
        stop_distance  = atr * stop_atr_multiple               # 2× ATR
        stop_pct       = stop_distance / price

        if stop_pct <= 0:
            return {"qty": 0.0, "notional": 0.0, "risk_pct": 0.0}

        raw_notional = risk_dollars / stop_pct

        # Hard cap 1: max 5% of capital at risk per trade
        max_risk_notional = capital * self.MAX_SINGLE_RISK_PCT / (stop_pct + 1e-9)
        # Hard cap 2: max 30% of capital as notional
        max_notional_cap  = capital * self.MAX_NOTIONAL_PCT

        position_value = min(raw_notional, max_risk_notional, max_notional_cap)

        qty = position_value / price

        # Safety assertion — will raise loudly if caps fail
        assert position_value <= capital * self.MAX_NOTIONAL_PCT + 1e-6, \
            f"RISK BUG: notional {position_value:.2f} > 30% of capital {capital:.2f}"
        assert (position_value * stop_pct) <= capital * self.MAX_SINGLE_RISK_PCT + 1e-6, \
            f"RISK BUG: risk ${position_value * stop_pct:.2f} > 5% of capital {capital:.2f}"

        return {
            "qty":      qty,
            "notional": position_value,
            "risk_pct": self.BASE_RISK_PCT,
            "regime":   regime,
            "mult":     1.0,
        }

    # ── Circuit Breakers ─────────────────────────────────────────────────────

    def check_daily_drawdown(self, start_capital: float, current_capital: float) -> bool:
        """Returns True if daily drawdown >= 3% (HALT threshold)."""
        if start_capital <= 0:
            return False
        dd = (start_capital - current_capital) / start_capital
        if dd >= self.MAX_DAILY_DRAWDOWN:
            log.critical(
                f"DAILY CIRCUIT BREAKER: drawdown={dd:.2%} >= {self.MAX_DAILY_DRAWDOWN:.0%}"
            )
            return True
        return False

    def check_weekly_drawdown(self, week_start_capital: float, current_capital: float) -> bool:
        """Returns True if weekly drawdown >= 8% (HALT until Monday 00:00 UTC)."""
        if week_start_capital <= 0:
            return False
        dd = (week_start_capital - current_capital) / week_start_capital
        if dd >= self.MAX_WEEKLY_DRAWDOWN:
            log.critical(
                f"WEEKLY CIRCUIT BREAKER: drawdown={dd:.2%} >= {self.MAX_WEEKLY_DRAWDOWN:.0%}. "
                f"Halting until next Monday 00:00 UTC."
            )
            return True
        return False

    def is_new_week(self, date_str: str) -> bool:
        """Returns True if date_str is a Monday (start of new trading week)."""
        try:
            return datetime.strptime(date_str, "%Y-%m-%d").weekday() == 0
        except Exception:
            return False

    # ── Adaptive stops (unchanged API) ───────────────────────────────────────

    def calculate_adaptive_stops(self,
                                  price: float,
                                  atr:   float,
                                  regime: str,
                                  side:  str = "LONG") -> dict:
        """
        Phase 9.5: balanced — 1.8×ATR stop, 5.4×ATR TP (3:1 RR).
        """
        sl_dist = atr * 1.8
        tp_dist = atr * 5.4

        if side == "LONG":
            return {"stop": price - sl_dist, "tp": price + tp_dist,
                    "sl_mult": 1.8, "tp_mult": 5.4}
        else:
            return {"stop": price + sl_dist, "tp": price - tp_dist,
                    "sl_mult": 1.8, "tp_mult": 5.4}

    def validate_trade(self, side, entry, stop, tp, qty, capital, current_heat=0.0) -> bool:
        if entry <= 0 or stop <= 0 or qty <= 0:
            return False
        risk   = abs(entry - stop)
        reward = abs(tp - entry)
        if risk == 0:
            return False
        if reward / risk < self.MIN_RR_RATIO:
            log.info(f"RR too low: {reward/risk:.2f} < {self.MIN_RR_RATIO}")
            return False
        new_heat = current_heat + (risk / entry) * (qty * entry / capital)
        if new_heat > self.MAX_PORTFOLIO_HEAT:
            log.info(f"Portfolio heat {new_heat:.2%} > {self.MAX_PORTFOLIO_HEAT:.0%}")
            return False
        return True

    def get_stop_loss(self, side, entry, atr, regime="NEUTRAL") -> float:
        return self.calculate_adaptive_stops(entry, atr, regime, side)["stop"]

    def get_take_profit(self, side, entry, atr, regime="NEUTRAL") -> float:
        return self.calculate_adaptive_stops(entry, atr, regime, side)["tp"]

    def get_smart_trailing_stop(self, side, current, entry, atr, last_stop) -> float:
        profit_pct  = abs(current - entry) / entry
        trail_mult  = 1.5 if profit_pct < 0.02 else 0.7
        if side == "LONG":
            return max(last_stop, current - trail_mult * atr)
        else:
            return min(last_stop, current + trail_mult * atr)

    # ── Stubs kept for import compatibility ──────────────────────────────────

    async def run_loop(self, interval: int = 1): pass
    async def check_drawdown(self) -> bool: return True
    async def check_cooldown(self, strategy: str) -> bool: return False
    async def validate_trade_signal(self, *args, **kwargs) -> bool: return True
    async def validate_trade_execution(self, *args, **kwargs) -> tuple: return True, 0.0
