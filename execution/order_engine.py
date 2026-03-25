"""
execution/order_engine.py
Binance Futures Async Order Engine — Phase 4
"""

import os
import json
import asyncio
import logging
from binance import AsyncClient
from binance.exceptions import BinanceAPIException
from core.state_manager import StateManager
from config import SYMBOLS

log = logging.getLogger("OrderEngine")

class OrderEngine:
    def __init__(self, state: StateManager, portfolio_risk=None):
        self.state = state
        self.portfolio_risk = portfolio_risk
        self.running = False
        
        self.dry_run = os.getenv('DRY_RUN', 'false').lower() == 'true'
        self.use_testnet = os.getenv('BINANCE_TESTNET', 'true').lower() == 'true'
        
        self.api_key = os.getenv('BINANCE_TEST_API_KEY')
        self.api_secret = os.getenv('BINANCE_TEST_API_SECRET')
        self.client: AsyncClient = None

    async def init_client(self):
        """Initialize AsyncClient and configure futures account."""
        self.client = await AsyncClient.create(
            api_key=self.api_key,
            api_secret=self.api_secret,
            testnet=True
        )
        # testnet=True natively configures python-binance to use testnet.binancefuture.com and wss://stream.binancefuture.com
        
        if not self.dry_run:
            for symbol in SYMBOLS:
                market_sym = symbol.replace('/', '').upper() 
                try:
                    await self.client.futures_change_margin_type(symbol=market_sym, marginType='ISOLATED')
                except BinanceAPIException:
                    pass
                try:
                    await self.client.futures_change_leverage(symbol=market_sym, leverage=3)
                except BinanceAPIException:
                    pass

    async def close_client(self):
        if self.client:
            await self.client.close_connection()

    async def run_loop(self, interval: int = 1):
        """Poll Redis for new order requests."""
        self.running = True
        log.info(f"🚀 Started Order Engine (Dry Run: {self.dry_run})")
        
        loops = 0
        while self.running:
            try:
                if not self.dry_run:
                    if not self.client:
                        await self.init_client()
                    
                    if loops % 60 == 0:
                        try:
                            acc = await self.client.futures_account()
                            await self.state.set('binance:account', acc)
                        except Exception as e:
                            log.warning(f"Could not fetch Binance account: {e}")
                            
                for symbol in SYMBOLS:
                    queue_key = f"order_request:{symbol}"
                    req = await self.state.get(queue_key)
                    if req:
                        success = await self._process_order(symbol, req)
                        if success:
                            await self.state.redis.delete(queue_key)
                        else:
                            # Do not crash, retry in 10s
                            await asyncio.sleep(10)
                        
                loops += 1
            except asyncio.CancelledError:
                break
            except Exception as e:
                log.error(f"[TESTNET ERROR] OrderEngine loop error: {e}, retrying in 30s")
                self.client = None
                await asyncio.sleep(30)
                
            await asyncio.sleep(interval)

    async def _process_order(self, symbol: str, req: dict):
        market_sym = symbol.replace('/', '').upper()
        action = req.get('action')
        side = req.get('side')
        qty = float(req.get('qty', 0))
        price = float(req.get('price', 0))

        if self.dry_run:
            log.info(f"📝 PAPER TRADE: {side} {market_sym} qty={qty}")
            await self._log_signal(price, side, action, req.get('strategy', 'AI'))
            return True

        try:
            # 0. Validate and Round
            valid, qty, price, sl, tp = self._validate_and_round(market_sym, side, qty, price, req.get('stop'), req.get('tp'))
            if not valid:
                log.error(f"❌ Order validation failed for {market_sym}")
                return True # Toss invalid requests to avoid loop
                
            if action == 'OPEN':
                # --- PHASE 8: PORTFOLIO RISK GATING ---
                if self.portfolio_risk:
                    current_positions = await self.state.get_all_positions()
                    if not await self.portfolio_risk.validate_portfolio_impact(symbol, qty * price, current_positions):
                        log.warning(f"🛡️ Portfolio Risk rejection for {symbol}")
                        return True # Drop restricted order

                # Retry logic for network blips
                for attempt in range(3):
                    try:
                        await self._execute_open(market_sym, side, qty, price, sl, tp, req.get('strategy', 'AI'))
                        break
                    except Exception as e:
                        if attempt == 2: raise e
                        await asyncio.sleep(2 ** attempt)
                
                # Signal logging...
                await self._log_signal(price, side, 'OPEN', req.get('strategy', 'AI'))
            elif action == 'CLOSE':
                await self._execute_close(market_sym, side, qty)
                await self._log_signal(price, side, 'CLOSE', req.get('strategy', 'AI'))
            return True
        except Exception as e:
            log.error(f"🔥 Process Order Error: {e}")
            return False

    def _validate_and_round(self, symbol: str, side: str, qty: float, price: float, stop: float = None, tp: float = None):
        """Dynamic rounding and sanity checks."""
        try:
            # Dynamic rounding based on symbol
            if 'BTC' in symbol:
                qty, price = round(qty, 3), round(price, 1)
                sl, tp = round(stop or 0, 1), round(tp or 0, 1)
                min_qty = 0.001
            elif 'ETH' in symbol:
                qty, price = round(qty, 2), round(price, 2)
                sl, tp = round(stop or 0, 2), round(tp or 0, 2)
                min_qty = 0.01
            else:
                # Generic for altcoins
                qty, price = round(qty, 1), round(price, 4)
                sl, tp = round(stop or 0, 4), round(tp or 0, 4)
                min_qty = 0.1
                
            if qty < min_qty:
                log.warning(f"⚠️ Qty {qty} too small for {symbol} (min {min_qty})")
                return False, 0, 0, 0, 0
            
            return True, qty, price, sl, tp
        except Exception as e:
            log.error(f"Error in _validate_and_round: {e}")
            return False, 0, 0, 0, 0

    async def _log_signal(self, price, side, action, strategy):
        try:
            from datetime import datetime
            signal = {
                'time': datetime.utcnow().timestamp(),
                'price': price,
                'type': side,
                'action': action,
                'strategy': strategy,
                'pnl': 0
            }
            await self.state.redis.lpush('signals:history', json.dumps(signal))
            await self.state.redis.ltrim('signals:history', 0, 99)
        except: pass

    async def _execute_open(self, symbol: str, side: str, qty: float, price: float, stop: float, tp: float, strategy: str = 'UNKNOWN'):
        main_side = 'BUY' if side == 'LONG' else 'SELL'
        qty_str = f"{qty}" # Already rounded
        
        log.info(f"🚀 [REAL ORDER] OPEN {side} {symbol} qty={qty_str} @ {price}")
        
        # Log signal for chart
        try:
            from datetime import datetime
            signal = {
                'time': datetime.utcnow().timestamp(),
                'price': price,
                'type': side,
                'action': 'OPEN',
                'strategy': 'UNKNOWN', # In _execute_open we don't have req, but we can pass it
                'pnl': 0
            }
            # We'll need a better way to pass strategy name here. 
            # I'll modify the signature or use a global.
            # For now I'll modify _process_order to log signals instead.
        except: pass
        
        main_order = await self.client.futures_create_order(
            symbol=symbol,
            side=main_side,
            type='MARKET',
            quantity=qty_str
        )
        log.info(f"[TESTNET FILLED] order_id={main_order['orderId']}")

        exit_side = 'SELL' if side == 'LONG' else 'BUY'

        if stop and stop > 0:
            stop_price = round(stop, 1)
            await self.client.futures_create_order(
                symbol=symbol,
                side=exit_side,
                type='STOP_MARKET',
                stopPrice=stop_price,
                closePosition='true',
                timeInForce='GTC'
            )
            
        if tp and tp > 0:
            tp_price = round(tp, 1)
            await self.client.futures_create_order(
                symbol=symbol,
                side=exit_side,
                type='TAKE_PROFIT_MARKET',
                stopPrice=tp_price,
                closePosition='true',
                timeInForce='GTC'
            )
            
    async def _execute_close(self, symbol: str, side: str, qty: float):
        exit_side = 'SELL' if side == 'LONG' else 'BUY'
        qty_str = f"{qty:.3f}" if 'BTC' in symbol else f"{qty:.2f}"
        
        log.info(f"[TESTNET ORDER] CLOSE {side} {symbol} qty={qty_str}")
        
        try:
            close_order = await self.client.futures_create_order(
                symbol=symbol,
                side=exit_side,
                type='MARKET',
                quantity=qty_str,
                reduceOnly='true'
            )
            log.info(f"[TESTNET FILLED] order_id={close_order['orderId']}")
        except BinanceAPIException as e:
            if e.code == -2022:
                log.warning(f"⚠️ [TESTNET] ReduceOnly rejected for {symbol}: No position to close on exchange.")
            else:
                raise e
        
        await self.client.futures_cancel_all_open_orders(symbol=symbol)
