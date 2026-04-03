"""
core/multi_strategy_manager.py
Multi-Strategy Orchestrator — Phase 22
Registers multiple strategies and ensures isolated capital allocation.
"""

import logging
import asyncio
from datetime import datetime
from typing import Dict, List, Optional
from core.state_manager import StateManager

log = logging.getLogger("MultiStrategyManager")

class MultiStrategyManager:
    def __init__(self, state: StateManager, total_capital: float):
        self.state = state
        self.total_capital = total_capital
        
        # Default Allocations (can be overridden by config)
        self.allocations = {
            'scalper': 0.10,      # 10%
            'swing': 0.25,        # 25%
            'position': 0.40,     # 40%
            'ai_ensemble': 0.10,  # 10%
            'mean_reversion': 0.05, # 5%
            'ensemble_voting': 0.10 # 10%
        }
        
        # Per-strategy risk limits
        self.max_positions = {
            'scalper': 5,
            'swing': 3,
            'position': 2,
            'ai_ensemble': 2,
            'mean_reversion': 2,
            'ensemble_voting': 2
        }

    async def get_active_trades(self, strategy: str) -> List[dict]:
        """Fetch active trades for a strategy from Redis."""
        key = f"strategy:trades:{strategy}"
        trades_raw = await self.state.get(key) or []
        return trades_raw

    async def rebalance(self):
        """
        Dynamic Capital Rebalancing (Phase 3).
        Adjusts weights based on 7-day Sharpe and Net PnL.
        """
        try:
            new_allocs = {}
            scores = {}
            
            for strategy in self.allocations:
                # Fetch metrics
                sharpe = await self.state.get_float(f"metrics:{strategy}:sharpe") or 0.0
                pnl = await self.state.get_float(f"stats:{strategy}:pnl") or 0.0
                
                # Performance Score (Simple weighted combination)
                # Sharpe is primary, PnL is secondary
                score = max(0.1, (sharpe * 0.7) + (pnl / (self.total_capital * 0.01 + 1e-9) * 0.3))
                scores[strategy] = score
                
            total_score = sum(scores.values())
            
            # Normalize and smooth (Max 5% shift per rebalance)
            for strategy, score in scores.items():
                target = score / total_score
                current = self.allocations[strategy]
                
                # Smoothing (exponential moving average style or capped step)
                change = target - current
                clamped_change = max(-0.05, min(0.05, change))
                self.allocations[strategy] = max(0.05, current + clamped_change)
            
            # Final Normalization to ensure sum = 1.0
            norm_factor = sum(self.allocations.values())
            for s in self.allocations:
                self.allocations[s] /= norm_factor
                
            await self.state.set("manager:allocations", self.allocations)
            log.info(f"⚖️ Rebalanced Allocations: { {k: round(v,3) for k,v in self.allocations.items()} }")
            
        except Exception as e:
            log.error(f"Rebalance error: {e}")

    async def get_regime_multiplier(self, strategy: str) -> float:
        """
        Returns a multiplier [0.3 to 1.5] based on market regime vs strategy fit.
        """
        regime_data = await self.state.get("market:regime:global") or {}
        regime = regime_data.get('regime', 'NEUTRAL')
        
        # Strategy-Regime Fit Map (Expert-Grade Phase 6)
        # 1.0 = standard allocation
        fits = {
            'scalper':        {
                'TRENDING_BULL': 1.0, 'TRENDING_BEAR': 1.0, 
                'HIGH_VOL_CHOP': 1.5, 'LOW_VOL_ACCUMULATION': 0.8
            },
            'swing':          {
                'TRENDING_BULL': 1.5, 'TRENDING_BEAR': 1.5, 
                'HIGH_VOL_CHOP': 0.3, 'LOW_VOL_ACCUMULATION': 0.6
            },
            'ai_ensemble':    {
                'TRENDING_BULL': 1.3, 'TRENDING_BEAR': 1.3, 
                'HIGH_VOL_CHOP': 0.5, 'LOW_VOL_ACCUMULATION': 1.0
            },
            'mean_reversion': {
                'HIGH_VOL_CHOP': 1.5, 'TRENDING_BULL': 0.5, 
                'TRENDING_BEAR': 0.5, 'LOW_VOL_ACCUMULATION': 1.2
            }
        }
        
        strategy_fits = fits.get(strategy.lower(), {})
        return strategy_fits.get(regime, 1.0)

    async def can_open_trade(self, strategy: str, symbol: str, required_capital: float) -> bool:
        """
        Gating logic with Dynamic Allocation and Regime Multipliers.
        """
        active_trades = await self.get_active_trades(strategy)
        
        # 1. Position Count Limit
        if len(active_trades) >= self.max_positions.get(strategy, 1):
            log.warning(f"🚫 {strategy} at max positions ({len(active_trades)})")
            return False
            
        # 2. Dynamic Capital Limit (Regime-Conditioned)
        base_pct = self.allocations.get(strategy, 0)
        regime_mult = await self.get_regime_multiplier(strategy)
        
        effective_pct = base_pct * regime_mult
        strategy_total_cap = self.total_capital * effective_pct
        
        current_utilized = sum(t.get('nominal_value', 0) for t in active_trades)
        
        if (current_utilized + required_capital) > strategy_total_cap:
            log.warning(f"🚫 {strategy} capital exhausted: {current_utilized}/{strategy_total_cap:.0f} (Regime Mult: {regime_mult:.1f})")
            return False
            
        # 3. Symbol Conflict
        for t in active_trades:
            if t['symbol'] == symbol:
                log.warning(f"🚫 {strategy} already has active trade on {symbol}")
                return False
                
        return True

    async def get_total_exposure(self) -> float:
        """Calculate total exposure across all strategies."""
        total = 0
        for strategy in self.allocations:
            trades = await self.get_active_trades(strategy)
            total += sum(t.get('nominal_value', 0) for t in trades)
        return total
