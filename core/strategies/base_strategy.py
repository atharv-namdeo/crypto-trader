import asyncio
import logging
import os
from core.state_manager import StateManager
from core.pnl_tracker import PnLTracker
from core.risk import RiskManager
from config import SYMBOLS

log = logging.getLogger("BaseStrategy")

class BaseStrategy:
    """Standardized strategy interface."""
    def __init__(self, state: StateManager, pnl_tracker: PnLTracker, manager=None, capital: float = 200.0):
        self.state = state
        self.pnl = pnl_tracker
        self.manager = manager
        # If manager is provided, use its allocation; otherwise use fixed capital
        if manager:
            self.capital = manager.total_capital * manager.allocations.get(self.__class__.__name__.lower(), 0.1)
        else:
            self.capital = capital
            
        self.risk = RiskManager(state)
        self.running = False
        self.name = self.__class__.__name__
        self.symbols = SYMBOLS

    async def run(self, interval: int = 60):
        """Standard execution loop."""
        self.running = True
        log.info(f"🚀 Strategy {self.name} Started")
        
        while self.running:
            try:
                for symbol in self.symbols:
                    await self._process(symbol)
            except Exception as e:
                log.error(f"Error in {self.name} process loop: {e}")
            await asyncio.sleep(interval)

    async def _process(self, symbol: str):
        """Override this in child classes."""
        pass

    async def _open_position(self, symbol: str, side: str, price: float, confidence: float):
        """Standard wrapper for opening a position with risk validation."""
        # This is a simplified placeholder for the actual order logic
        # In a real bot, this would call the OrderEngine
        log.info(f"📡 {self.name} requesting {side} on {symbol} at {price}")
        # (Order logic here)

    async def _close_position(self, symbol: str, pos: dict, price: float, reason: str):
        """Standard wrapper for closing a position."""
        log.info(f"📡 {self.name} closing {symbol} at {price} | Reason: {reason}")
        # (Order logic here)
