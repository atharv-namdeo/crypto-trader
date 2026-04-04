"""
multi_algo_executor.py
Parallel Multi-Algorithm Execution Engine — Autonomous Trading Engine

Responsibilities:
- Runs all compatible strategies in parallel across all symbols
- Each symbol is assigned its best-fit strategy (via StrategySelector)
- Tracks per-strategy performance metrics (Sharpe, win rate, profit factor)
- Auto-retires underperforming strategies per symbol
"""

import asyncio
import logging
from datetime import datetime
from typing import Dict, List, Optional

from strategy_selector import StrategySelector
from advanced_risk_engine import AdvancedRiskEngine
from config import SYMBOLS

log = logging.getLogger("MultiAlgoExecutor")

# Interval (seconds) between full scan cycles
SCAN_INTERVAL = 60

# Timeframes each strategy naturally operates on
STRATEGY_TIMEFRAMES: Dict[str, str] = {
    "scalper":        "1m",
    "swing":          "1h",
    "position":       "4h",
    "ai_ensemble":    "1h",
    "mean_reversion": "1h",
    "ensemble_voting": "1h",
}


class MultiAlgoExecutor:
    """
    Parallel execution engine.
    Spawns concurrent workers for all (symbol, strategy) pairs that the
    StrategySelector deems appropriate, then updates live metrics.
    """

    def __init__(self, state, order_engine):
        self.state = state
        self.order_engine = order_engine
        self.selector = StrategySelector(state)
        self.risk_engine = AdvancedRiskEngine(state)
        self.running = False
        self._active_tasks: Dict[str, asyncio.Task] = {}

    # ------------------------------------------------------------------
    # Main loop
    # ------------------------------------------------------------------

    async def run_loop(self):
        """
        Continuous orchestration loop.
        Every SCAN_INTERVAL seconds:
          1. Re-evaluate regime → strategy mapping for all symbols
          2. Generate signals in parallel
          3. Execute qualifying trades
          4. Update performance metrics
        """
        self.running = True
        log.info("🤖 MultiAlgoExecutor started")

        while self.running:
            try:
                await self._scan_and_execute()
            except Exception as exc:
                log.error(f"Executor scan error: {exc}")
            await asyncio.sleep(SCAN_INTERVAL)

    def stop(self):
        self.running = False

    # ------------------------------------------------------------------
    # Core scanning logic
    # ------------------------------------------------------------------

    async def _scan_and_execute(self):
        """Single scan-and-execute pass across all symbols."""
        # Build {symbol: best_strategy} map
        symbol_strategy_map = await self.selector.build_symbol_strategy_map(SYMBOLS)

        # Dispatch signal + execution for each symbol concurrently
        tasks = [
            self._process_symbol(symbol, strategy)
            for symbol, strategy in symbol_strategy_map.items()
        ]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        for symbol, result in zip(symbol_strategy_map.keys(), results):
            if isinstance(result, Exception):
                log.debug(f"[{symbol}] process error: {result}")

        # Update strategy performance metrics
        await self._update_performance_metrics()

    async def _process_symbol(self, symbol: str, strategy: str):
        """
        For a single (symbol, strategy) pair:
        1. Check trade gate (can_open, sharpe, consecutive losses)
        2. Generate multi-timeframe signal
        3. Validate signal quality
        4. Calculate position size via Kelly + regime risk
        5. Submit order request
        """
        # Gate 1: strategy-level allow/throttle
        allowed, reason = await self.selector.should_trade(strategy, symbol)
        if not allowed:
            log.debug(f"🚫 [{strategy}] {symbol}: {reason}")
            return

        # Gate 2: existing position check
        existing_pos = await self.state.get_position(symbol)
        if existing_pos:
            return  # Already in a position on this symbol

        # Generate a signal using the ensemble algorithm (works for all strategies)
        signal = await self._generate_signal(symbol, strategy)
        if not signal or signal.get("action") in ("NEUTRAL", "HOLD", None):
            return

        # Gate 3: signal quality (liquidity, volatility, EMA alignment, confirmations)
        valid, reason = await self.risk_engine.validate_trade(symbol, signal)
        if not valid:
            log.debug(f"⚠️  [{strategy}] {symbol} signal rejected: {reason}")
            return

        action = signal["action"]  # "BUY" or "SELL"
        price = signal.get("price", 0)
        atr = signal.get("atr", price * 0.01)
        regime = signal.get("regime", "NEUTRAL")
        capital = await self.state.get_float("portfolio:value") or 1000.0

        # Position sizing
        qty = await self.risk_engine.calculate_position_size(strategy, symbol, capital, price)

        # Regime-aware stops
        stops = self.risk_engine.calculate_adaptive_stops(
            price=price,
            atr=atr,
            regime=regime,
            side="LONG" if action == "BUY" else "SHORT",
        )

        # Submit order request to state (picked up by OrderEngine)
        order_req = {
            "symbol": symbol,
            "action": "OPEN",
            "side": "LONG" if action == "BUY" else "SHORT",
            "qty": qty,
            "price": price,
            "sl": stops["sl"],
            "tp": stops["tp"],
            "strategy": strategy,
            "regime": regime,
            "confidence": signal.get("confidence", 0),
            "timestamp": int(datetime.utcnow().timestamp() * 1000),
        }

        await self.state.set(f"order_request:{symbol}", order_req)
        log.info(
            f"🚀 [{strategy}] {symbol} {action} | Price={price:.4f} "
            f"Qty={qty:.6f} SL={stops['sl']:.4f} TP={stops['tp']:.4f} "
            f"Regime={regime} Conf={signal.get('confidence', 0):.2f}"
        )

    # ------------------------------------------------------------------
    # Signal generation
    # ------------------------------------------------------------------

    async def _generate_signal(self, symbol: str, strategy: str) -> Optional[Dict]:
        """
        Generate a signal enriched with price, ATR, EMA, volume, and regime data.
        Delegates to the EnsembleAlgorithm for the heavy lifting and decorates
        the result with the additional fields required by AdvancedRiskEngine.validate_trade.
        """
        try:
            from core.strategies.ensemble_algorithm import EnsembleAlgorithm

            algo = EnsembleAlgorithm(self.state)
            base_signal = await algo.generate_signal(symbol)

            if not base_signal:
                return None

            # Enrich with raw market data
            tf = STRATEGY_TIMEFRAMES.get(strategy, "1h")
            df = await self.state.get_df(f"ohlcv:{tf}:{symbol}", n=60)
            if df is None or df.empty:
                return base_signal

            from core.utils import compute_atr, compute_ema

            closes = df["close"]
            price = float(closes.iloc[-1])
            atr = float(compute_atr(df, window=14).iloc[-1]) if len(df) >= 14 else price * 0.01
            ema_20 = float(compute_ema(closes, 20).iloc[-1]) if len(df) >= 20 else price
            ema_50 = float(compute_ema(closes, 50).iloc[-1]) if len(df) >= 50 else price
            volume_24h = float(df["volume"].tail(24).sum()) * price if len(df) >= 24 else 0

            # Hourly volatility (std of returns)
            returns = closes.pct_change().dropna()
            volatility = float(returns.tail(24).std()) if len(returns) >= 24 else 0

            # Market regime for this symbol
            regime_data = await self.state.get(f"market:regime:{symbol}") or {}
            regime = regime_data.get("regime", "NEUTRAL")

            # Count signal confirmations (short / medium / long components)
            components = base_signal.get("components", {})
            buy_votes = sum(
                1 for c in components.values()
                if c.get("action") in ("BUY",)
            )
            sell_votes = sum(
                1 for c in components.values()
                if c.get("action") in ("SELL",)
            )

            action = base_signal.get("action", "NEUTRAL")
            confirmations = buy_votes if action == "BUY" else sell_votes if action == "SELL" else 0

            base_signal.update(
                {
                    "price": price,
                    "atr": atr,
                    "ema_20": ema_20,
                    "ema_50": ema_50,
                    "volume_24h": volume_24h,
                    "volatility": volatility,
                    "regime": regime,
                    "confirmations": confirmations,
                    "required_confirmations": 2,
                }
            )
            return base_signal

        except Exception as exc:
            log.error(f"_generate_signal [{symbol}]: {exc}")
            return None

    # ------------------------------------------------------------------
    # Performance tracking
    # ------------------------------------------------------------------

    async def _update_performance_metrics(self):
        """
        Compute and cache per-strategy Sharpe ratio, win rate, and profit factor
        from the trade history stored in Redis.
        """
        try:
            import json
            import numpy as np

            if not self.state.redis:
                return

            history_raw = await self.state.redis.lrange("trade:history", 0, 499)
            if not history_raw:
                return

            all_trades = [json.loads(t) for t in history_raw]

            strategies = {t.get("strategy", "unknown") for t in all_trades}
            for strategy in strategies:
                trades = [t for t in all_trades if t.get("strategy", "").lower() == strategy.lower()]
                if len(trades) < 3:
                    continue

                pnls = [t.get("pnl_net", t.get("pnl", 0)) for t in trades]
                arr = np.array(pnls)

                wins = arr[arr > 0]
                losses = arr[arr <= 0]
                win_rate = len(wins) / len(arr)
                profit_factor = (wins.sum() / (abs(losses.sum()) + 1e-9)) if len(losses) > 0 else float("inf")

                # Sharpe (annualised, assume ~1h average trade duration as proxy)
                mean_r = arr.mean()
                std_r = arr.std() + 1e-9
                sharpe = (mean_r / std_r) * (252 ** 0.5)  # annualise

                await self.state.set(f"metrics:{strategy}:sharpe", round(float(sharpe), 4))
                await self.state.set(f"metrics:{strategy}:win_rate", round(float(win_rate), 4))
                await self.state.set(f"metrics:{strategy}:profit_factor", round(float(profit_factor), 4))
                await self.state.set(f"metrics:{strategy}:total_trades", len(trades))

        except Exception as exc:
            log.error(f"_update_performance_metrics error: {exc}")
