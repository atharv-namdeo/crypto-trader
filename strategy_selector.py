"""
strategy_selector.py
Intelligent Strategy Routing — Autonomous Trading Engine
Dynamically selects the best algorithm for each symbol based on market regime,
recent performance metrics, and per-timeframe signal quality.
"""

import logging
from typing import Dict, Optional, Tuple

log = logging.getLogger("StrategySelector")

# Regime → Strategy fit matrix.  Values are relative preference scores (higher = better fit).
REGIME_STRATEGY_FIT: Dict[str, Dict[str, float]] = {
    "TRENDING_BULL": {
        "swing":          1.5,
        "position":       1.4,
        "ai_ensemble":    1.2,
        "scalper":        0.9,
        "mean_reversion": 0.4,
        "ensemble_voting": 1.1,
    },
    "TRENDING_BEAR": {
        "swing":          1.4,
        "position":       1.3,
        "ai_ensemble":    1.2,
        "scalper":        1.0,
        "mean_reversion": 0.4,
        "ensemble_voting": 1.0,
    },
    "HIGH_VOL_CHOP": {
        "scalper":        1.3,
        "mean_reversion": 1.5,
        "ai_ensemble":    0.8,
        "swing":          0.3,
        "position":       0.3,
        "ensemble_voting": 0.7,
    },
    "LOW_VOL_ACCUMULATION": {
        "position":       1.4,
        "swing":          1.1,
        "mean_reversion": 1.2,
        "ai_ensemble":    1.0,
        "scalper":        0.7,
        "ensemble_voting": 1.0,
    },
    "TRENDING_NEUTRAL": {
        "swing":          1.2,
        "position":       1.2,
        "ai_ensemble":    1.1,
        "scalper":        1.0,
        "mean_reversion": 0.8,
        "ensemble_voting": 1.1,
    },
    "NEUTRAL": {
        "ai_ensemble":    1.2,
        "ensemble_voting": 1.1,
        "swing":          1.0,
        "position":       1.0,
        "scalper":        1.0,
        "mean_reversion": 1.0,
    },
}

# Minimum Sharpe ratio below which a strategy is considered underperforming
MIN_SHARPE_THRESHOLD = -0.3

# Strategies with Sharpe below this value are abandoned in dynamic selection
ABANDON_SHARPE = -0.5


class StrategySelector:
    """
    Selects the best-fit strategy for a given (symbol, regime) pair.
    Combines static regime fit scores with live Sharpe-ratio performance.
    """

    def __init__(self, state):
        self.state = state
        # All strategies that can be routed to
        self.all_strategies = list(REGIME_STRATEGY_FIT["NEUTRAL"].keys())

    async def select_best_strategy(
        self,
        symbol: str,
        regime: str,
        top_n: int = 1,
    ) -> str:
        """
        Return the name of the best strategy for the given symbol and regime.

        Args:
            symbol:  Trading pair (e.g. "BTC/USDT").
            regime:  Market regime string from RegimeDetector.
            top_n:   How many top candidates to consider (picks the best by combined score).

        Returns:
            Strategy name string (e.g. "swing", "scalper").
        """
        scored = await self._score_strategies(regime)
        if not scored:
            return "ai_ensemble"  # safe fallback

        return scored[0][0]

    async def select_top_strategies(
        self,
        regime: str,
        n: int = 3,
    ) -> list:
        """Return the top-n strategy names for the current regime."""
        scored = await self._score_strategies(regime)
        return [name for name, _ in scored[:n]]

    async def _score_strategies(self, regime: str) -> list:
        """
        Compute combined scores for all strategies.
        Score = regime_fit * 0.5 + normalized_sharpe * 0.5
        Strategies below ABANDON_SHARPE are excluded.
        Returns list of (strategy_name, combined_score) sorted descending.
        """
        fit_map = REGIME_STRATEGY_FIT.get(regime, REGIME_STRATEGY_FIT["NEUTRAL"])
        scored = []

        for strategy in self.all_strategies:
            fit_score = fit_map.get(strategy, 1.0)

            # Fetch live Sharpe ratio (defaults to 0 if not yet available)
            sharpe = await self.state.get_float(f"metrics:{strategy}:sharpe") or 0.0

            # Discard strategies that are actively losing
            if sharpe < ABANDON_SHARPE:
                log.debug(f"🚫 Skipping {strategy} — Sharpe {sharpe:.2f} below abandon threshold")
                continue

            # Normalize sharpe to [0, 2] range for scoring (clamp between -1 and 3)
            norm_sharpe = (max(-1.0, min(3.0, sharpe)) + 1.0) / 2.0

            combined = fit_score * 0.5 + norm_sharpe * 0.5
            scored.append((strategy, combined))

        scored.sort(key=lambda x: x[1], reverse=True)
        return scored

    async def get_regime_for_symbol(self, symbol: str) -> str:
        """Fetch the cached regime for a specific symbol, falling back to global."""
        regime_data = await self.state.get(f"market:regime:{symbol}") or {}
        if regime_data.get("regime"):
            return regime_data["regime"]

        # Fallback: global (BTC-based) regime
        global_data = await self.state.get("market:regime:global") or {}
        return global_data.get("regime", "NEUTRAL")

    async def build_symbol_strategy_map(self, symbols: list) -> Dict[str, str]:
        """
        For every symbol, determine the best strategy to use right now.
        Returns a dict: {symbol: strategy_name}
        """
        result = {}
        for symbol in symbols:
            regime = await self.get_regime_for_symbol(symbol)
            best = await self.select_best_strategy(symbol, regime)
            result[symbol] = best
            log.debug(f"📊 {symbol} | Regime: {regime} → Strategy: {best}")
        return result

    async def should_trade(self, strategy: str, symbol: str) -> Tuple[bool, str]:
        """
        Quick gate: check whether a strategy is currently fit to trade a symbol.
        Returns (allowed: bool, reason: str).
        """
        sharpe = await self.state.get_float(f"metrics:{strategy}:sharpe") or 0.0
        if sharpe < ABANDON_SHARPE:
            return False, f"Sharpe {sharpe:.2f} too low"

        consecutive_losses = int(await self.state.get_float(f"metrics:{strategy}:consecutive_losses") or 0)
        if consecutive_losses >= 5:
            return False, f"{consecutive_losses} consecutive losses — throttled"

        return True, "ok"
