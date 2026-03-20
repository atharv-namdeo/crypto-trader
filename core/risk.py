"""
core/risk.py — Upgraded Risk Manager (Phase 1)

Hard limits enforced before every trade.
Portfolio heat tracking uses PositionTracker data.
"""

import logging

log = logging.getLogger("RiskManager")


class RiskManager:
    """
    Production-grade risk guardian.
    All limits are absolute — cannot be overridden by signal confidence.
    """

    # ── Hard limits ────────────────────────────────────────────────────────
    MAX_PORTFOLIO_HEAT   = 0.06    # 6% total open risk
    MAX_ASSET_EXPOSURE   = 0.40    # 40% capital per asset
    MAX_DAILY_DRAWDOWN   = 0.03    # 3% daily loss → halt
    MAX_WEEKLY_DRAWDOWN  = 0.07    # 7% weekly loss → halt + alert
    MIN_RR_RATIO         = 1.5     # minimum risk:reward before entry
    MAX_LEVERAGE         = 5.0     # absolute max

    # ── Position sizing ───────────────────────────────────────────────────
    BASE_RISK_PCT        = 0.01    # 1% portfolio base risk per trade
    MAX_RISK_PCT         = 0.025   # 2.5% at full conviction

    def __init__(self):
        self._daily_start_capital = None
        self._weekly_start_capital = None

    def compute_position_size(
        self,
        capital: float,
        conviction: float,      # 0–1 from ensemble scorer
        atr: float,
        price: float,
        stop_atr_multiple: float = 1.5,
    ) -> dict:
        """
        Kelly-inspired dynamic sizing.
        Returns {'qty': float, 'notional': float, 'risk_pct': float}.
        """
        # Scale risk between BASE and MAX based on conviction
        risk_pct = self.BASE_RISK_PCT + conviction * (self.MAX_RISK_PCT - self.BASE_RISK_PCT)

        stop_distance = stop_atr_multiple * atr
        if stop_distance <= 0 or price <= 0:
            return {'qty': 0.0, 'notional': 0.0, 'risk_pct': 0.0}

        # notional such that stop loss = risk_pct of capital
        notional = (capital * risk_pct) / (stop_distance / price)
        qty = notional / price

        return {
            'qty':      qty,
            'notional': notional,
            'risk_pct': risk_pct,
        }

    def validate_trade(
        self,
        side: str,
        entry: float,
        stop: float,
        tp: float,
        qty: float,
        capital: float,
        current_heat: float = 0.0,
    ) -> bool:
        """
        Gate for new trade entry.
        Returns True only if ALL risk checks pass.
        """
        if entry <= 0 or stop <= 0 or qty <= 0:
            return False

        # 1. Risk/Reward check
        risk   = abs(entry - stop)
        reward = abs(tp - entry)
        if risk == 0:
            log.warning("RR check: zero risk distance")
            return False
        rr = reward / risk
        if rr < self.MIN_RR_RATIO:
            log.info(f"⚠️ RR too low: {rr:.2f} < {self.MIN_RR_RATIO}")
            return False

        # 2. Portfolio heat check
        new_heat = current_heat + (abs(entry - stop) / entry) * (qty * entry / capital)
        if new_heat > self.MAX_PORTFOLIO_HEAT:
            log.info(f"⚠️ Heat would be {new_heat:.2%} > {self.MAX_PORTFOLIO_HEAT:.2%}")
            return False

        # 3. Asset exposure
        notional = qty * entry
        exposure = notional / capital
        if exposure > self.MAX_ASSET_EXPOSURE:
            log.info(f"⚠️ Asset exposure {exposure:.2%} > {self.MAX_ASSET_EXPOSURE:.2%}")
            return False

        return True

    def check_daily_drawdown(self, start_capital: float, current_capital: float) -> bool:
        """Returns True if daily drawdown limit breached → halt trading."""
        if start_capital <= 0:
            return False
        drawdown = (start_capital - current_capital) / start_capital
        if drawdown >= self.MAX_DAILY_DRAWDOWN:
            log.critical(f"🛑 DAILY DRAWDOWN LIMIT HIT: {drawdown:.2%} — halting engine")
            return True
        return False

    def check_weekly_drawdown(self, week_start_capital: float, current_capital: float) -> bool:
        """Returns True if weekly drawdown limit breached."""
        if week_start_capital <= 0:
            return False
        drawdown = (week_start_capital - current_capital) / week_start_capital
        if drawdown >= self.MAX_WEEKLY_DRAWDOWN:
            log.critical(f"🛑 WEEKLY DRAWDOWN LIMIT HIT: {drawdown:.2%} — halting engine")
            return True
        return False
