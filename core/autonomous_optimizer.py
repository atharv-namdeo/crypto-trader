"""
core/autonomous_optimizer.py
Main Operational Orchestrator — Phase 1 (Autonomous)

The "Brain" of the engine that coordinates strategy selection, 
capital allocation, and parallel execution.
"""

import asyncio
import logging
from datetime import datetime
from typing import List, Dict, Any
from core.state_manager import StateManager
from core.strategy_selector import StrategySelector
from core.multi_strategy_manager import MultiStrategyManager
from execution.multi_algo_executor import MultiAlgoExecutor
from execution.order_engine import OrderEngine

log = logging.getLogger("AutonomousOptimizer")

class AutonomousOptimizer:
    def __init__(self, state: StateManager, order_engine: OrderEngine):
        self.state = state
        self.selector = StrategySelector(state)
        self.manager = MultiStrategyManager(state, total_capital=1000.0) # Capital from state/config
        self.executor = MultiAlgoExecutor(state, order_engine)
        
        self.running = False
        self.last_rebalance = 0
        self.rebalance_interval = 3600 # 1 hour
        self.assignment_interval = 300 # 5 minutes

    async def run_autonomous_loop(self):
        """
        Main autonomous loop that runs in the background.
        """
        self.running = True
        log.info("🧠 Autonomous Optimizer: Heartbeat started")
        
        while self.running:
            try:
                now = datetime.now().timestamp()
                
                # 1. Update Strategy Assignments (Intelligent Routing)
                await self.selector.update_assignments()
                
                # 2. Performance-Based Rebalancing (Dynamic Weights)
                if now - self.last_rebalance > self.rebalance_interval:
                    await self.manager.rebalance()
                    self.last_rebalance = now
                    log.info("⚖️ Autonomous Optimizer: Capital rebalancing complete")

                # 3. Collect Signals from all registered strategy outcomes
                # (In this architecture, signals are usually pushed to Redis by strategy processes)
                # This loop can check a signal queue or trigger a poll.
                await self._poll_and_execute_signals()
                
                # 4. State Updates for Dashboard
                await self.state.set("engine:autonomous_heartbeat", now)
                
                await asyncio.sleep(self.assignment_interval)
                
            except Exception as e:
                log.error(f"Autonomous Optimizer: Loop error: {e}")
                await asyncio.sleep(60)

    async def _poll_and_execute_signals(self):
        """
        Gathers signals from the multi-strategy signal queue in Redis.
        """
        try:
            # Strategies push to 'signal_queue' in Redis
            # We fetch all and pass to executor
            signal_raw = await self.state.get("signal_queue") or []
            if signal_raw:
                await self.executor.handle_signals(signal_raw)
                # Clear queue after processing
                await self.state.set("signal_queue", [])
        except Exception as e:
            log.error(f"Signal polling error: {e}")

    def stop(self):
        self.running = False
        log.info("🧠 Autonomous Optimizer: Stopped")
