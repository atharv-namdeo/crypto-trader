"""
core/strategy_selector.py
Intelligent Routing Engine — Phase 1 (Autonomous)

Analyzes market regimes for each coin and assigns the optimal strategy.
Updates assignments every 5 minutes.
"""

import logging
from typing import Dict, Optional, List
from core.state_manager import StateManager
from config import SYMBOLS

log = logging.getLogger("StrategySelector")

class StrategySelector:
    def __init__(self, state: StateManager):
        self.state = state
        
        # Expert-Grade Strategy Mapping
        self.regime_map = {
            'EARLY_BULL_BREAKOUT': 'swing',
            'MATURE_BULL_EXTENSION': 'position',
            'BULL_PARABOLIC_EXHAUSTION': 'ai_ensemble',
            'EARLY_BEAR_BREAKDOWN': 'swing',
            'MATURE_BEAR_DECLINE': 'position',
            'BEAR_VOLATILITY_BOTTOM': 'ai_ensemble',
            'CONSOLIDATION_NARROW': None, # Institutional Skip
            'CONSOLIDATION_WIDE': None,   # Institutional Skip
            'HIGH_VOL_CHOP': None,        # Capital preservation mode
            'ACCUMULATION_PHASE': None    # Institutional Skip
        }

    async def update_assignments(self):
        """
        Iterates through all configured symbols and assigns the best strategy.
        Results are stored in Redis: 'strategy_assignment:{symbol}'
        """
        try:
            assignments = {}
            global_regime_data = await self.state.get("market:regime:global") or {}
            global_regime = global_regime_data.get('regime', 'CONSOLIDATION_WIDE')
            
            log.info(f"🔄 Strategy Selector: Updating assignments (Global Regime: {global_regime})")
            
            for symbol in SYMBOLS:
                # 1. Fetch Local Regime
                local_regime_data = await self.state.get(f"market:regime:{symbol}") or {}
                local_regime = local_regime_data.get('regime', global_regime)
                
                # 2. Determine Strategy
                selected = self.regime_map.get(local_regime, "ensemble")
                
                # 3. Override if Global Regime is HIGH_VOL_CHOP (System-wide risk off)
                if global_regime == 'HIGH_VOL_CHOP':
                    selected = None
                
                assignments[symbol] = selected
                
                # 4. Save to Redis
                await self.state.set(f"strategy_assignment:{symbol}", selected)
                
            # Store full mapping for metadata/dashboard
            await self.state.set("manager:strategy_assignments", assignments)
            
            count = len([v for v in assignments.values() if v])
            log.info(f"✅ Strategy Selector: {count}/{len(SYMBOLS)} symbols assigned active strategies.")
            
            return assignments
            
        except Exception as e:
            log.error(f"Strategy selection update error: {e}")
            return {}

    def get_required_quorum(self, regime: str) -> int:
        """
        Volatility-Adjusted Quorum (Dynamic Alpha Calibration v7.0)
        """
        # 1. Catch Alpha in Confirmed Trends (2-Indicator Quorum)
        if "BULL" in regime:
            return 2
        if "BEAR" in regime and "EARLY" not in regime:
            return 2
            
        # 2. Block Traps in Transitions/Early Phases (3-Indicator Quorum)
        if "CONSOLIDATION" in regime or "CHOP" in regime or "EARLY" in regime:
            return 3
        if "CORRECTION" in regime or "BOUNCE" in regime:
            return 3
            
        return 2 # Default

    async def get_strategy_for_symbol(self, symbol: str) -> Optional[str]:
        """Helper to get current assignment from Redis."""
        return await self.state.get(f"strategy_assignment:{symbol}")
