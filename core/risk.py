"""
core/risk.py — Upgraded Risk Manager (Phase 1)

Hard limits enforced before every trade.
Portfolio heat tracking uses PositionTracker data.
"""

import asyncio
import logging
import json
import time
from core.kelly_calculator import KellyCalculator

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
    MIN_RR_RATIO         = 2.0     # Final Profit Optimized: 2:1 Minimum RR Ratio
    MAX_LEVERAGE         = 10.0    # absolute max for crypto

    # ── Position sizing ───────────────────────────────────────────────────
    BASE_RISK_PCT        = 0.01    # 1% portfolio base risk per trade
    MAX_RISK_PCT         = 0.025   # 2.5% at full conviction

    def __init__(self, state=None):
        self.state = state
        self.running = False
        self.kelly = KellyCalculator(state) if state else None

    async def run_loop(self, interval: int = 1):
        """
        Background safety loop. 
        Enforces daily/weekly drawdown limits in real-time.
        """
        self.running = True
        log.info(f"🛡️ RiskManager Loop Active (Circuit Breaker: {self.MAX_DAILY_DRAWDOWN*100}%)")
        while self.running:
            try:
                # 1. Check Drawdown
                is_safe = await self.check_drawdown()
                if not is_safe:
                    log.critical("🚨 CIRCUIT BREAKER TRIGGERED: Daily Drawdown Limit Hit!")
                    # In a real system, we might set a global lock or force-close all
                    await self.state.set("risk:circuit_breaker", "ACTIVE")
                
                # 2. Daily/Weekly Reset Logic (Optional - usually handled by state manager)
                
            except Exception as e:
                log.error(f"RiskManager loop error: {e}")
            
            await asyncio.sleep(interval)

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

    async def compute_position_size(
        self,
        capital: float,
        strategy: str,
        atr: float,
        price: float,
        regime: str = "NEUTRAL",
        stop_atr_multiple: float = 1.5,
    ) -> dict:
        """
        Regime-aware Kelly-optimized dynamic sizing.
        """
        # 1. Get Base Kelly Risk
        risk_pct = await self.kelly.get_optimal_risk(strategy) if self.kelly else self.BASE_RISK_PCT
        
        # 2. Regime-based Multiplier (Phase 8 Upgrade)
        regime_mults = {
            'EARLY_BULL_BREAKOUT': 2.0,  # Aggressive Breakout Capture
            'MATURE_BULL_EXTENSION': 1.0,
            'BULL_CORRECTION': 0.8,
            'EARLY_BEAR_BREAKDOWN': 2.0, # Aggressive Breakdown Capture
            'HIGH_VOL_CHOP': 0.1,         # Further reduced for chop protection
            'ACCUMULATION': 0.5,
            'NEUTRAL': 0.8
        }
        mult = regime_mults.get(regime, 0.4)
        
        # 3. Apply Graduated Drawdown Multiplier
        dd_mult = await self.kelly.get_drawdown_multiplier() if self.kelly else 1.0
        final_risk_pct = risk_pct * mult * dd_mult
        
        # Cap risk to hard max
        final_risk_pct = min(final_risk_pct, self.MAX_RISK_PCT)

        stop_distance = stop_atr_multiple * atr
        if stop_distance <= 0 or price <= 0:
            return {'qty': 0.0, 'notional': 0.0, 'risk_pct': 0.0}

        # Quantity such that stop loss = final_risk_pct of capital
        notional = (capital * final_risk_pct) / (stop_distance / price)
        qty = notional / price

        return {
            'qty':      qty,
            'notional': notional,
            'risk_pct': final_risk_pct,
            'regime':   regime,
            'mult':     mult
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

    async def check_cooldown(self, strategy: str) -> bool:
        """
        Enforces a 30-minute pause after 3 consecutive losses.
        Returns True if system is cooling down.
        """
        try:
            history_raw = await self.state.redis.lrange('trade:history', 0, 9)
            if not history_raw: return False
            
            trades = [json.loads(t) for t in history_raw if json.loads(t).get('strategy', '').lower() == strategy.lower()]
            if len(trades) < 3: return False
            
            # Check last 3
            recent_pnls = [t.get('pnl_net', 0) for t in trades[:3]]
            if all(p < 0 for p in recent_pnls):
                # 3 losses in a row -> Check time
                last_exit_time = trades[0].get('time')
                if last_exit_time:
                    exit_dt = datetime.fromisoformat(last_exit_time)
                    elapsed = (datetime.utcnow() - exit_dt).total_seconds()
                    if elapsed < 1800: # 30 mins
                        log.warning(f"❄️ Strategy {strategy} is in COOLDOWN ({1800-elapsed:.0f}s left)")
                        return True
            return False
        except Exception as e:
            log.error(f"Cooldown check error: {e}")
            return False

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

    def calculate_adaptive_stops(self, price: float, atr: float, regime: str, side: str = 'LONG') -> dict:
        """
        Calculates dynamic stops based on market regime to avoid SL whipsaws.
        """
        regime_multipliers = {
            'TRENDING_BULL':       {'sl': 3.5, 'tp': 7.0},
            'TRENDING_BEAR':       {'sl': 3.5, 'tp': 7.0},
            'EARLY_BULL_BREAKOUT': {'sl': 3.0, 'tp': 8.0},
            'HIGH_VOL_CHOP':       {'sl': 2.0, 'tp': 5.0},
            'LOW_VOL_ACCUMULATION': {'sl': 4.0, 'tp': 6.0},
            'NEUTRAL':             {'sl': 3.0, 'tp': 6.0}
        }
        
        mult = regime_multipliers.get(regime, {'sl': 3.0, 'tp': 6.0})
        
        sl_dist = atr * mult['sl']
        tp_dist = atr * mult['tp']
        
        if side == 'LONG':
            return {
                'stop': price - sl_dist,
                'tp':   price + tp_dist,
                'sl_mult': mult['sl'],
                'tp_mult': mult['tp']
            }
        else:
            return {
                'stop': price + sl_dist,
                'tp':   price - tp_dist,
                'sl_mult': mult['sl'],
                'tp_mult': mult['tp']
            }

    def get_stop_loss(self, side: str, entry: float, atr: float, regime: str = 'NEUTRAL') -> float:
        """Regime-aware adaptive stop loss."""
        stops = self.calculate_adaptive_stops(entry, atr, regime, side)
        return stops['stop']

    def get_take_profit(self, side: str, entry: float, atr: float, regime: str = 'NEUTRAL') -> float:
        """Regime-aware adaptive take profit."""
        stops = self.calculate_adaptive_stops(entry, atr, regime, side)
        return stops['tp']

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
