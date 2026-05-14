"""
execution/multi_algo_executor.py
Parallel Strategy Execution Layer — Phase 1 (Autonomous)

Handles simultaneous signal processing from multiple algorithms.
Enforces strategy-to-symbol routing and conflict resolution.
"""

import asyncio
import logging
from typing import List, Dict, Any, Optional
from core.state_manager import StateManager
from core.strategy_selector import StrategySelector
from core.advanced_risk_engine import AdvancedRiskEngine
from execution.order_engine import OrderEngine

log = logging.getLogger("MultiAlgoExecutor")

class MultiAlgoExecutor:
    def __init__(self, state: StateManager, order_engine: OrderEngine):
        self.state = state
        self.order_engine = order_engine
        self.selector = StrategySelector(state)
        self.risk_engine = AdvancedRiskEngine(state)
        
        # In-memory lock to prevent concurrent trades on same symbol
        self._symbol_locks: Dict[str, asyncio.Lock] = {}

    def _get_lock(self, symbol: str) -> asyncio.Lock:
        if symbol not in self._symbol_locks:
            self._symbol_locks[symbol] = asyncio.Lock()
        return self._symbol_locks[symbol]

    async def handle_signals(self, signals: List[Dict[str, Any]]):
        """
        Main entry point for multi-algo execution.
        Processes signals in parallel using asyncio.gather.
        """
        if not signals: return
        
        log.info(f"🚀 Multi-Algo: Processing {len(signals)} incoming signals...")
        
        tasks = [self.process_single_signal(sig) for sig in signals]
        await asyncio.gather(*tasks)

    async def process_single_signal(self, signal: Dict[str, Any]):
        """
        Validates and executes a single strategy signal.
        """
        symbol = signal.get('symbol')
        strategy = signal.get('strategy', '').lower()
        side = signal.get('side')
        
        if not symbol or not strategy or not side:
            log.warning(f"⚠️ Multi-Algo: Malformed signal received: {signal}")
            return

        async with self._get_lock(symbol):
            try:
                # 1. Routing Check: Is this strategy assigned to this symbol?
                assigned_strat = await self.selector.get_strategy_for_symbol(symbol)
                
                if assigned_strat != strategy:
                    log.debug(f"⏭️ Multi-Algo: Skipping {strategy} on {symbol} (Currently routed to {assigned_strat})")
                    return

                # 2. Duplicate Check: Are we already in a position?
                active_pos = await self.state.get(f"position:{symbol}")
                if active_pos:
                    log.debug(f"⏭️ Multi-Algo: Position already active on {symbol}. Skipping.")
                    return

                # 3. Risk Check: Get Optimal Size
                sizing = await self.risk_engine.get_optimal_size(strategy, symbol, signal.get('price', 0))
                
                # 4. Stop Logic: Get Adaptive SL/TP
                stops = await self.risk_engine.get_adaptive_stops(
                    symbol, side, signal.get('price', 0), signal.get('atr', 0)
                )

                # 5. Execution: Create Order
                order_params = {
                    'symbol': symbol,
                    'side': side,
                    'amount': sizing['amount'],
                    'price': signal.get('price'),
                    'stop_loss': stops['sl'],
                    'take_profit': stops['tp'],
                    'strategy': strategy,
                    'metadata': {
                        'regime': signal.get('regime'),
                        'kelly_risk': sizing['risk_pct'],
                        'sl_mult': stops['sl_mult']
                    }
                }
                
                log.info(f"🎯 Multi-Algo: Executing {strategy} {side} on {symbol} | Risk: {sizing['risk_pct']:.2%}")
                
                # Forward to low-level Order Engine
                success = await self.order_engine.create_order(**order_params)
                
                if success:
                    log.info(f"✅ Multi-Algo: Trade execution SUCCESS for {symbol}")
                else:
                    log.error(f"❌ Multi-Algo: Trade execution FAILED for {symbol}")

            except Exception as e:
                log.error(f"Multi-Algo: Error processing signal for {symbol}: {e}")
