import asyncio
import logging
from datetime import datetime
from core.state_manager import StateManager
from config import CAPITAL

log = logging.getLogger("SafetyCircuitBreaker")

class SafetyCircuitBreaker:
    """
    Expert Failsafe: Monitors portfolio health and halts execution if 
    drawdown limits are breached.
    """
    def __init__(self, state: StateManager, max_drawdown_pct=0.05):
        self.state = state
        self.max_drawdown_pct = max_drawdown_pct
        self.is_halted = False

    async def run_loop(self):
        log.info(f"🛡️ Safety Circuit Breaker Active (Limit: {self.max_drawdown_pct*100}%)")
        while True:
            try:
                # 1. Fetch current equity
                equity = await self.state.get_float('portfolio:equity') or float(CAPITAL)
                initial_capital = float(CAPITAL)
                
                # 2. Calculate Drawdown
                drawdown = (initial_capital - equity) / initial_capital
                
                if drawdown >= self.max_drawdown_pct and not self.is_halted:
                    await self.halt_trading(drawdown)
                
                await asyncio.sleep(10) # 10s check resolution
            except Exception as e:
                log.error(f"Circuit breaker error: {e}")
                await asyncio.sleep(30)

    async def halt_trading(self, current_dd):
        self.is_halted = True
        log.critical(f"🛑 CIRCUIT BREAKER TRIGGERED! Drawdown: {current_dd*100:.2f}%")
        
        # 1. Set global halt flag in state
        await self.state.set("system:halted", True)
        await self.state.set("system:halt_reason", f"Drawdown limit reached: {current_dd*100:.2f}%")
        
        # 2. Send Telegram Alert
        # (Assuming telegram notifier is accessible or sending via StateManager)
        log.info("📢 Halting all order execution...")
        
        # In a real scenario, we would iterate and close all positions here.
        # For now, it alerts and stops new orders via the 'system:halted' flag.

    @classmethod
    async def is_system_safe(cls, state: StateManager):
        halted = await state.get("system:halted")
        return not halted
