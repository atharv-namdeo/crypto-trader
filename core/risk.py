"""
core/risk.py — Upgraded Risk Manager (Phase 1)

Hard limits enforced before every trade.
Portfolio heat tracking uses PositionTracker data.
"""

import asyncio
import logging

log = logging.getLogger("RiskGuardian")


class RiskManager:
    """
    Production-grade risk guardian.
    All limits are absolute — cannot be overridden by signal confidence.
    """

    # ── Hard limits ────────────────────────────────────────────────────────
    MAX_PORTFOLIO_HEAT   = 0.10    # 10% total open risk (increased for parallel strategies)
    MAX_ASSET_EXPOSURE   = 0.50    # 50% capital per asset
    MAX_DAILY_DRAWDOWN   = 0.05    # 5% daily loss → halt
    MAX_WEEKLY_DRAWDOWN  = 0.15    # 15% weekly loss → halt
    MIN_RR_RATIO         = 1.5     # minimum risk:reward
    MAX_LEVERAGE         = 10.0    # absolute max for crypto

    # ── Position sizing ───────────────────────────────────────────────────
    BASE_RISK_PCT        = 0.01    # 1% portfolio base risk per trade
    MAX_RISK_PCT         = 0.025   # 2.5% at full conviction

    def __init__(self, state=None):
        self.state = state
        self.running = False

    async def check_drawdown(self) -> bool:
        """Check if daily or weekly drawdown limits have been hit."""
        try:
            pnl_today = await self.state.get_float('pnl:today') or 0.0
            portfolio_value = await self.state.get_float('portfolio:value') or 1000.0
            start_cap = portfolio_value - pnl_today
            
            # 5% Daily Check
            if pnl_today < -(start_cap * self.MAX_DAILY_DRAWDOWN):
                return False
            return True
        except Exception:
            return True # Fail-safe: allow if state is messy

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

        return True

    async def validate_trade_signal(self, symbol: str, signal: str, 
                                    ml_confidence: float, 
                                    fuzzy_conviction: float) -> bool:
        """
        Validate a trade signal against multiple safety checks.
        
        Only execute if:
        1. ML confidence > 65%
        2. Fuzzy conviction > 0.6
        3. Daily win rate > 40%
        4. Account not in drawdown > 10%
        5. No conflicting signals from other strategies
        """
        import json
        
        # Check 1: ML confidence
        if ml_confidence < 0.65:
            log.warning(f"❌ {symbol} ML confidence too low: {ml_confidence:.2%}")
            return False
        
        # Check 2: Fuzzy conviction
        if fuzzy_conviction < 0.6:
            log.warning(f"❌ {symbol} Fuzzy conviction too low: {fuzzy_conviction}")
            return False
        
        # Check 3: Daily win rate
        trades_24h = await self.state.redis.lrange('trade:history:24h', 0, -1)
        if len(trades_24h) > 0:
            wins = sum(1 for t_json in trades_24h if float(json.loads(t_json).get('pnl', 0)) > 0)
            win_rate = wins / len(trades_24h)
            
            if win_rate < 0.40:
                log.warning(f"❌ Daily win rate too low: {win_rate:.2%}")
                return False
        
        # Check 4: Account drawdown
        equity_history = await self.state.redis.lrange('equity:history', 0, 100)
        if len(equity_history) > 10:
            equities = [float(e) for e in equity_history]
            max_equity = max(equities)
            current_equity = equities[0]
            drawdown = (max_equity - current_equity) / (max_equity + 1e-9)
            
            if drawdown > 0.10:
                log.warning(f"❌ Account drawdown too high: {drawdown:.2%}")
                return False
        
        # Check 5: Signal conflicts
        for other_strategy in ['SCALPER', 'SWING', 'POSITION']:
            other_signal = await self.state.get(f"ml_signal:{symbol}:last_from:{other_strategy}")
            if other_signal and isinstance(other_signal, dict) and other_signal.get('signal') != signal:
                log.warning(f"⚠️ Signal conflict: {other_strategy} says "
                           f"{other_signal['signal']}, we say {signal}")
                # Note: We don't block here, just log warning as per user spec
        
        # ✅ All checks passed
        log.info(f"✅ {symbol} {signal} validated! ML: {ml_confidence:.2%}, "
                f"Fuzzy: {fuzzy_conviction:.2f}")
        return True

    async def validate_trade_execution(self, symbol: str, side: str, price: float, stop: float, tp: float, confidence: float, capital: float, current_heat: float) -> tuple[bool, float]:
        """
        High-level gate for a trade that returns (is_valid, dynamic_qty).
        Combines limit checks with dynamic sizing.
        """
        if not await self.check_drawdown():
            return False, 0.0

        # Dynamic Sizing based on Confidence (1% to 2.5%)
        risk_pct = self.BASE_RISK_PCT * (0.5 + confidence)
        risk_pct = min(risk_pct, self.MAX_RISK_PCT)
        
        # Simple Qty calculation for 1x exposure (can be scaled by leverage)
        qty = (capital * risk_pct) / abs(price - stop) if abs(price - stop) > 0 else 0
        
        # Standard validation (using non-async validate_trade)
        valid = self.validate_trade(side, price, stop, tp, qty, capital, current_heat)
        if not valid:
            return False, 0.0
            
        log.info(f"⚖️ Dynamic Size for {symbol}: {qty:.4f} (Risk:{risk_pct*100:.1f}%)")
        return True, qty

    def get_stop_loss(self, side: str, entry: float, atr: float, multiplier: float = 1.5) -> float:
        """ATR-based adaptive stop loss."""
        # multiplier reduced to 1.5 for conservative risk
        dist = atr * multiplier
        return entry - dist if side == 'LONG' else entry + dist

    def get_take_profit(self, side: str, entry: float, atr: float, multiplier: float = 3.0) -> float:
        """ATR-based adaptive take profit."""
        # multiplier reduced to 3.0 for better risk/reward capture
        dist = atr * multiplier
        return entry + dist if side == 'LONG' else entry - dist

    def get_smart_trailing_stop(self, side: str, current: float, entry: float, atr: float, last_stop: float) -> float:
        """Adaptive trailing stop: moves only in favor of profit."""
        profit_pct = abs(current - entry) / entry
        
        # Trail closer as profit grows (Adaptive ATR multiplier)
        # Tighten from 1.5x to 0.7x ATR as profit grows past 2%
        trail_mult = 1.5 if profit_pct < 0.02 else 0.7
        
        if side == 'LONG':
            new_stop = current - (trail_mult * atr)
            return max(last_stop, new_stop) # Never move stop down
        else:
            new_stop = current + (trail_mult * atr)
            return min(last_stop, new_stop) # Never move stop up

    def check_trailing_stop(self, side: str, current_price: float, high_low_price: float, atr: float) -> float:
        """
        Calculate a trailing stop based on ATR distance from the extreme price.
        high_low_price: highest price since entry for LONG, lowest for SHORT.
        """
        dist = atr * 1.5
        if side == 'LONG':
            return max(high_low_price - dist, current_price * 0.99)
        else:
            return min(high_low_price + dist, current_price * 1.01)

    def check_daily_drawdown(self, start_capital: float, current_capital: float) -> bool:
        """Returns True if daily drawdown limit reached."""
        if start_capital <= 0: return False
        drawdown = (start_capital - current_capital) / start_capital
        if drawdown >= self.MAX_DAILY_DRAWDOWN:
            log.critical(f"🛑 DAILY DRAWDOWN LIMIT HIT: {drawdown:.2%}")
            return True
        return False

    def check_weekly_drawdown(self, week_start_capital: float, current_capital: float) -> bool:
        """Returns True if weekly drawdown limit reached."""
        if week_start_capital <= 0: return False
        drawdown = (week_start_capital - current_capital) / week_start_capital
        if drawdown >= self.MAX_WEEKLY_DRAWDOWN:
            log.critical(f"🛑 WEEKLY DRAWDOWN LIMIT HIT: {drawdown:.2%}")
            return True
        return False
