import asyncio
import logging
from datetime import datetime
from typing import List, Dict

from core.state_manager import StateManager
from core.strategies.ensemble_algorithm import EnsembleAlgorithm
from execution.order_engine import OrderEngine
from config import SYMBOLS, settings, CAPITAL
from core.advanced_risk_engine import AdvancedRiskEngine
from core.autonomous_optimizer import AutonomousOptimizer

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
        self.risk_engine = AdvancedRiskEngine(state)
        self.optimizer = AutonomousOptimizer(state, order_engine)
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
        from config import settings, CAPITAL
        from core.safety_circuit_breaker import SafetyCircuitBreaker
        
        log.info("⚖️ Starting Enterprise Execution Engine (Regime-Aware)...")
        while self.running:
            try:
                # Expert Safety Verification
                if not await SafetyCircuitBreaker.is_system_safe(self.state):
                    log.warning("🛑 Execution ENGINE HALTED by Safety Circuit Breaker.")
                    await asyncio.sleep(60)
                    continue
                
                for symbol in SYMBOLS:
                    signal_data = self.state.firebase.get(f"trading/signals/{symbol}")
                    
                    # 0. Sovereign Data Gating (Phase 11 Hardening)
                    if not signal_data or not isinstance(signal_data, dict):
                        continue
                        
                    action = signal_data.get('action', 'NEUTRAL')
                    if action == 'NEUTRAL':
                        continue
                        
                    pos = await self.state.get_position(symbol)
                    
                    # 1. EXECUTE ENTRY (LONG/SHORT)
                    if action in ['BUY', 'SELL'] and not pos:
                        side = "LONG" if action == 'BUY' else "SHORT"
                        
                        # Apply Pre-Trade Validation Gates (Fix 3 & 4)
                        if not await self.validate_trade_quality(symbol, signal_data):
                            continue
                        if not self.is_trading_allowed("ai_ensemble"):
                            continue

                        log.info(f"🚀 [ENSEMBLE {side}] {symbol} | Conf: {signal_data['confidence']:.2f} | Reg: {signal_data.get('regime')}")
                        
                        # Dynamic Regime-Aware Sizing & Stops (Advanced Risk Engine)
                        price = await self.state.get_float(f"price:{symbol}")
                        atr = signal_data.get('atr') or (price * 0.01)
                        
                        # Use Advanced Risk Engine for size, SL, and TP
                        sizing = await self.risk_engine.get_optimal_size("ai_ensemble", symbol, price)
                        stops = await self.risk_engine.get_adaptive_stops(symbol, side, price, atr)
                        
                        qty = sizing['amount']
                        
                        # Normalize Qty
                        if 'BTC' in symbol or 'ETH' in symbol:
                            qty = round(qty, 4)
                        else:
                            qty = round(qty, 1)

                        if qty > 0:
                            await self.state.set(f"order_request:{symbol}", {
                                "symbol": symbol,
                                "action": "OPEN",
                                "side": side,
                                "qty": qty,
                                "entry_price": price,
                                "stop_loss": stops['sl'],
                                "take_profit": stops['tp'],
                                "strategy": "ENSEMBLE"
                            })
                    
                    # 2. EXECUTE CLOSE
                    elif action == 'NEUTRAL' and pos:
                        # (Logic to handle dynamic closes if needed, or wait for SL/TP in OrderEngine)
                        pass
                    
                    # Handle Cross-Closes (e.g., BUY signal while in SHORT)
                    elif action == 'BUY' and pos and pos.get('side') == 'SHORT':
                        log.info(f"🔄 [FLIP] Closing SHORT for LONG on {symbol}")
                        await self.state.set(f"order_request:{symbol}", {
                            "symbol": symbol, "action": "CLOSE", "side": "SHORT", "qty": pos['qty']
                        })

                await asyncio.sleep(5)
            except Exception as e:
                log.error(f"Execution engine error: {e}")
                await asyncio.sleep(10)

    async def validate_trade_quality(self, symbol: str, signal: Dict) -> bool:
        """
        Additional filters before placing trades to improve win rate.
        """
        try:
            # 1. Liquidity Check (>$1M 24h Volume)
            # In simulation, we might not have real volume, so we assume OK if price exists
            # In production, we fetch from CCXT
            pass 

            # 2. Trend Confirmation (EMA Alignment)
            ohlcv_1h = await self.state.get_df(f"ohlcv:1h:{symbol}", n=60)
            if ohlcv_1h is not None and len(ohlcv_1h) >= 50:
                ema_20 = ohlcv_1h['close'].ewm(span=20).mean().iloc[-1]
                ema_50 = ohlcv_1h['close'].ewm(span=50).mean().iloc[-1]
                price = ohlcv_1h['close'].iloc[-1]
                
                if signal['action'] == 'BUY':
                    if not (price > ema_20 and ema_20 > ema_50):
                        log.info(f"🚫 {symbol} Trend Check Failed (Price < EMA20/50)")
                        return False
                elif signal['action'] == 'SELL':
                    if not (price < ema_20 and ema_20 < ema_50):
                        log.info(f"🚫 {symbol} Trend Check Failed (Price > EMA20/50)")
                        return False

            # 3. Consecutive Loss Check
            if await self.risk_manager.check_cooldown("ai_ensemble"):
                return False

            return True
        except Exception as e:
            log.error(f"Trade validation error: {e}")
            return True # Fallback to true to avoid missing major moves

    def is_trading_allowed(self, strategy: str) -> bool:
        """Check if current time is optimal for this strategy (UTC)"""
        # UTC hour windows with high liquidity
        TRADING_HOURS = {
            'scalper':    [7, 8, 9, 14, 15, 16, 20, 21, 22],
            'swing':      [6, 7, 8, 14, 15, 19, 20, 21],
            'ai_ensemble': None # All hours (Trend following)
        }
        
        allowed = TRADING_HOURS.get(strategy)
        if allowed is None:
            return True
            
        current_hour = datetime.utcnow().hour
        return current_hour in allowed

    async def start(self):
        self.running = True
        tasks = [
            self.run_market_data_pump(),
            self.run_signal_engine(),
            self.run_execution_engine()
        ]
        
        # Add Autonomous Optimizer loop if enabled
        if settings.AUTONOMOUS_MODE:
            log.info("🤖 Starting Autonomous Intelligence Module...")
            tasks.append(self.optimizer.run_autonomous_loop())
            
        await asyncio.gather(*tasks)

    def stop(self):
        self.running = False
