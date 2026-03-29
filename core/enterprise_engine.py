import asyncio
import logging
from datetime import datetime
from typing import List

from core.state_manager import StateManager
from core.strategies.ensemble_algorithm import EnsembleAlgorithm
from execution.order_engine import OrderEngine
from config import SYMBOLS

log = logging.getLogger("EnterpriseEngine")

class EnterpriseTradingEngine:
    """
    Orchestrates the 3-Layer Cloud Stack:
    Railway (Backend) <-> Firebase (DB) <-> Binance (Execution)
    """
    
    def __init__(self, state: StateManager, order_engine: OrderEngine):
        self.state = state
        self.order_engine = order_engine
        self.algorithm = EnsembleAlgorithm(state)
        self.running = False

    async def run_market_data_pump(self):
        """Continuously sync top symbol prices to Firebase."""
        log.info("📡 Starting Market Data Pump...")
        while self.running:
            try:
                for symbol in SYMBOLS[:20]: # Priority sync for top 20
                    price = await self.state.get_float(f"price:{symbol}")
                    if price:
                        # StateManager already mirrors price: keys, but we can add more rich data here
                        self.state.firebase.update(f"market/prices/{symbol}", {
                            "current_price": price,
                            "timestamp": int(datetime.utcnow().timestamp() * 1000)
                        })
                await asyncio.sleep(2) # 2s resolution for Firebase
            except Exception as e:
                log.error(f"Market pump error: {e}")
                await asyncio.sleep(5)

    async def run_signal_engine(self):
        """Generate high-conviction signals across multiple timeframes."""
        log.info("🧠 Starting Enterprise Signal Engine...")
        while self.running:
            try:
                tasks = [self.algorithm.generate_signal(s) for s in SYMBOLS]
                await asyncio.gather(*tasks)
                await asyncio.sleep(30) # Signal check every 30s
            except Exception as e:
                log.error(f"Signal engine error: {e}")
                await asyncio.sleep(10)

    async def run_execution_engine(self):
        """Monitor signals in Firebase and execute real orders on Binance."""
        log.info("⚖️ Starting Enterprise Execution Engine...")
        while self.running:
            try:
                for symbol in SYMBOLS:
                    # Read the ground truth signal from Firebase
                    signal_data = self.state.firebase.get(f"trading/signals/{symbol}")
                    
                    if not signal_data or signal_data.get('action') == 'NEUTRAL':
                        continue
                        
                    # Check for existing positions in Redis (hot state)
                    pos = await self.state.get_position(symbol)
                    
                    # 1. EXECUTE BUY
                    if signal_data['action'] == 'BUY' and not pos:
                        log.info(f"🚀 [ENSEMBLE BUY] {symbol} | Conf: {signal_data['confidence']:.2f}")
                        # Push order request to Redis so OrderEngine picks it up
                        # (OrderEngine is already refactored for real execution)
                        await self.state.set(f"order_request:{symbol}", {
                            "symbol": symbol,
                            "action": "OPEN",
                            "side": "LONG",
                            "qty": 0.001 if 'BTC' in symbol else 0.1, # Initial sizing logic
                            "price": signal_data['confidence'], # Placeholder for price logic if needed
                            "strategy": "ENSEMBLE"
                        })
                    
                    # 2. EXECUTE SELL
                    elif signal_data['action'] == 'SELL' and pos:
                        log.info(f"🔥 [ENSEMBLE SELL] {symbol} | Conf: {signal_data['confidence']:.2f}")
                        await self.state.set(f"order_request:{symbol}", {
                            "symbol": symbol,
                            "action": "CLOSE",
                            "side": "LONG",
                            "qty": pos['qty'],
                            "strategy": "ENSEMBLE"
                        })
                
                # Periodically sync all active orders to Firebase for dashboard
                if datetime.utcnow().second % 30 < 5: # Sync every ~30s
                    active_orders = await self.order_engine.get_active_orders()
                    await self.state.set("orders:active", active_orders)

                await asyncio.sleep(5) # Execution loop resolution
            except Exception as e:
                log.error(f"Execution engine error: {e}")
                await asyncio.sleep(10)

    async def start(self):
        self.running = True
        await asyncio.gather(
            self.run_market_data_pump(),
            self.run_signal_engine(),
            self.run_execution_engine()
        )

    def stop(self):
        self.running = False
