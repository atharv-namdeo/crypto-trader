"""
autonomous_optimizer.py
Main Orchestrator — Fully Autonomous Intelligent Trading Engine

Responsibilities:
- Coordinates StrategySelector, MultiAlgoExecutor, and AdvancedRiskEngine
- Detects market regime and routes capital accordingly
- Runs periodic rebalancing based on Sharpe ratios
- Provides a single entry-point coroutine for main.py
"""

import asyncio
import logging
from datetime import datetime
from typing import Dict, List

from strategy_selector import StrategySelector
from multi_algo_executor import MultiAlgoExecutor
from advanced_risk_engine import AdvancedRiskEngine
from config import SYMBOLS

log = logging.getLogger("AutonomousOptimizer")

# How often (seconds) to rebalance strategy capital allocations
REBALANCE_INTERVAL = 3600  # 1 hour

# How often (seconds) to emit a summary performance log
SUMMARY_INTERVAL = 300  # 5 minutes


class AutonomousOptimizer:
    """
    Top-level autonomous trading orchestrator.

    This class wires together:
    - MultiAlgoExecutor   → parallel signal generation + order submission
    - StrategySelector    → regime-aware strategy routing
    - AdvancedRiskEngine  → Kelly sizing & regime-adaptive stops
    - MultiStrategyManager (from existing codebase) → allocation rebalancing

    No user input is required after instantiation.
    """

    def __init__(self, state, order_engine):
        self.state = state
        self.order_engine = order_engine

        self.selector = StrategySelector(state)
        self.risk_engine = AdvancedRiskEngine(state)
        self.executor = MultiAlgoExecutor(state, order_engine)

        self.running = False
        self._last_rebalance: datetime = datetime.min
        self._last_summary: datetime = datetime.min

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def run_loop(self):
        """
        Main coroutine.  Start this as an asyncio task in main.py.

        The loop:
        1. Keeps the MultiAlgoExecutor running (signals + orders)
        2. Periodically rebalances capital allocation across strategies
        3. Emits performance summaries to logs (and optionally Telegram)
        """
        self.running = True
        log.info("🤖 Autonomous Optimizer started — no manual input needed")

        # Start the executor in its own task
        executor_task = asyncio.create_task(
            self.executor.run_loop(), name="MULTI_ALGO_EXECUTOR"
        )

        while self.running:
            try:
                now = datetime.utcnow()

                # Periodic rebalancing
                if (now - self._last_rebalance).total_seconds() >= REBALANCE_INTERVAL:
                    await self._rebalance()
                    self._last_rebalance = now

                # Periodic summary
                if (now - self._last_summary).total_seconds() >= SUMMARY_INTERVAL:
                    await self._emit_summary()
                    self._last_summary = now

                # Check executor health
                if executor_task.done():
                    exc = executor_task.exception()
                    if exc:
                        log.error(f"Executor task failed ({exc}), restarting…")
                    executor_task = asyncio.create_task(
                        self.executor.run_loop(), name="MULTI_ALGO_EXECUTOR"
                    )

            except Exception as exc:
                log.error(f"AutonomousOptimizer loop error: {exc}")

            await asyncio.sleep(30)

        executor_task.cancel()

    def stop(self):
        self.running = False
        self.executor.stop()

    # ------------------------------------------------------------------
    # Rebalancing
    # ------------------------------------------------------------------

    async def _rebalance(self):
        """
        Dynamically redistribute capital across strategies using Sharpe ratios.
        Mirrors the logic in MultiStrategyManager.rebalance() but also handles
        the StrategySelector's regime-fit layer.
        """
        log.info("⚖️  Starting autonomous capital rebalance…")
        try:
            strategies = list(self.selector.all_strategies)
            scores: Dict[str, float] = {}

            for strategy in strategies:
                sharpe = await self.state.get_float(f"metrics:{strategy}:sharpe") or 0.0
                win_rate = await self.state.get_float(f"metrics:{strategy}:win_rate") or 0.5
                # Exclude strategies below the abandon threshold
                if sharpe < -0.5:
                    scores[strategy] = 0.0
                    continue
                # Combined score: 70% Sharpe + 30% win-rate (min 0 so normalisation is stable)
                score = max(0.0, sharpe * 0.7 + win_rate * 0.3)
                scores[strategy] = score

            total = sum(scores.values()) + 1e-9
            new_allocs = {s: round(v / total, 4) for s, v in scores.items()}

            # Persist to Redis so MultiStrategyManager reads it
            await self.state.set("manager:allocations", new_allocs)
            log.info(f"📊 New allocations: {new_allocs}")

        except Exception as exc:
            log.error(f"Rebalance error: {exc}")

    # ------------------------------------------------------------------
    # Performance summary
    # ------------------------------------------------------------------

    async def _emit_summary(self):
        """Log a concise performance dashboard to the console."""
        try:
            portfolio = await self.state.get_float("portfolio:value") or 0.0
            capital_key = await self.state.get_float("portfolio:initial") or portfolio or 1000.0
            pnl_pct = (portfolio - capital_key) / (capital_key + 1e-9) * 100

            lines = [
                "═" * 55,
                f"📊 AUTONOMOUS ENGINE — {datetime.utcnow().strftime('%H:%M:%S UTC')}",
                f"   Portfolio: ${portfolio:,.2f}  |  PnL: {pnl_pct:+.2f}%",
            ]

            global_regime = await self.state.get("market:regime:global") or {}
            regime_str = global_regime.get("regime", "UNKNOWN")
            lines.append(f"   Global Regime: {regime_str}")
            lines.append("   Strategy Performance:")

            for strategy in self.selector.all_strategies:
                sharpe = await self.state.get_float(f"metrics:{strategy}:sharpe") or 0.0
                win_rate = await self.state.get_float(f"metrics:{strategy}:win_rate") or 0.0
                trades = await self.state.get_float(f"metrics:{strategy}:total_trades") or 0
                alloc_data = await self.state.get("manager:allocations") or {}
                alloc = alloc_data.get(strategy, 0)
                lines.append(
                    f"     {strategy:18s} | Sharpe={sharpe:+.2f} "
                    f"WR={win_rate:.0%} Trades={int(trades)} Alloc={alloc:.0%}"
                )

            lines.append("═" * 55)
            for line in lines:
                log.info(line)

            # Sync to Firebase dashboard
            try:
                self.state.firebase.update(
                    "analytics/performance",
                    {
                        "portfolio_value": portfolio,
                        "pnl_pct": round(pnl_pct, 2),
                        "regime": regime_str,
                        "timestamp": int(datetime.utcnow().timestamp() * 1000),
                    },
                )
            except Exception:
                pass  # Firebase optional

        except Exception as exc:
            log.error(f"_emit_summary error: {exc}")
