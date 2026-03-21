"""
execution/order_engine.py
Binance Futures Async Order Engine — Phase 4
"""

import os
import json
import asyncio
import logging
from binance.client import AsyncClient
from binance.exceptions import BinanceAPIException
from core.state_manager import StateManager
from config import SYMBOLS

log = logging.getLogger("OrderEngine")

class OrderEngine:
    def __init__(self, state: StateManager):
        self.state = state
        self.running = False
        
        self.dry_run = os.getenv('DRY_RUN', 'true').lower() == 'true'
        self.use_testnet = True  # Forced to bypass geo-blocking        
        # Determine prefix for API keys
        prefix = 'BINANCE_TEST_' if self.use_testnet else 'BINANCE_'
        if not self.use_testnet and not os.getenv('BINANCE_API_KEY'):
            prefix = 'BINANCE_REAL_'
            
        self.api_key = os.getenv(f'{prefix}API_KEY', '')
        self.api_secret = os.getenv(f'{prefix}API_SECRET', '')
        self.client: AsyncClient = None

    async def init_client(self):
        """Initialize AsyncClient and configure futures account."""
        self.client = await AsyncClient.create(
            api_key=self.api_key,
            api_secret=self.api_secret,
            testnet=self.use_testnet
        )
        
        # Task 7 Requirements: Set ISOLATED margin and 3x Leverage
        if not self.dry_run:
            for symbol in SYMBOLS:
                market_sym = symbol.replace('/', '').upper()  # e.g. BTCUSDT
                try:
                    await self.client.futures_change_margin_type(symbol=market_sym, marginType='ISOLATED')
                    log.info(f"✅ Set {market_sym} margin type to ISOLATED")
                except BinanceAPIException as e:
                    if 'No need to change margin type' not in e.message:
                        log.warning(f"Could not set margin type for {market_sym}: {e.message}")
                        
                try:
                    await self.client.futures_change_leverage(symbol=market_sym, leverage=3)
                    log.info(f"✅ Set {market_sym} leverage to 3x")
                except BinanceAPIException as e:
                    log.error(f"Could not set leverage for {market_sym}: {e.message}")

    async def close_client(self):
        if self.client:
            await self.client.close_connection()

    async def run_loop(self, interval: int = 1):
        """Poll Redis for new order requests."""
        self.running = True
        log.info(f"🚀 Started Order Engine (Dry Run: {self.dry_run})")
        
        while self.running:
            try:
                if not self.dry_run:
                    if not self.client:
                        await self.init_client()
                    
                for symbol in SYMBOLS:
                    queue_key = f"order_request:{symbol}"
                    req = await self.state.get(queue_key)
                    if req:
                        await self._process_order(symbol, req)
                        # Delete request after processing so it doesn't trigger again
                        await self.state.redis.delete(queue_key)
                        
            except asyncio.CancelledError:
                break
            except Exception as e:
                log.error(f"OrderEngine error: {e}, retrying in 30s")
                self.client = None
                await asyncio.sleep(30)
                
            await asyncio.sleep(interval)

    async def _process_order(self, symbol: str, req: dict):
        """
        Process order_request:
        {
            'action': 'OPEN' | 'CLOSE',
            'side': 'LONG' | 'SHORT',
            'qty': 0.005,
            'price': 69000,
            'stop': 68500,
            'tp': 70000
        }
        """
        market_sym = symbol.replace('/', '').upper()
        action = req.get('action')
        side = req.get('side')
        qty = round(req.get('qty', 0), 5)
        
        log.info(f"📡 Processing Order Request: {action} {side} {qty} {market_sym}")

        if self.dry_run:
            log.info(f"🔬 [DRY RUN] Would execute {action} {side} {qty} {market_sym}")
            # Mock success by setting position state in Redis
            if action == 'OPEN':
                pos = {
                    'symbol': symbol, 'side': side, 'entry': req.get('price'),
                    'qty': qty, 'stop': req.get('stop'), 'tp': req.get('tp')
                }
                await self.state.set_position(symbol, pos)
            elif action == 'CLOSE':
                await self.state.redis.delete(f"position:{symbol}")
            return

        try:
            if action == 'OPEN':
                await self._execute_open(market_sym, side, qty, req.get('stop'), req.get('tp'))
                # If everything succeeded, write to Redis position state
                # Note: position sync is now also managed by PositionTracker logic,
                # but we can set the active status here representing actual exchange state.
                pos = {
                    'symbol': symbol, 'side': side, 'entry': req.get('price'),
                    'qty': qty, 'stop': req.get('stop'), 'tp': req.get('tp'),
                    'live': True
                }
                await self.state.set_position(symbol, pos)
                
            elif action == 'CLOSE':
                await self._execute_close(market_sym, side, qty)
                await self.state.redis.delete(f"position:{symbol}")
                
        except BinanceAPIException as e:
            log.error(f"❌ Binance API Error on {action} {market_sym}: {e.message}")
        except Exception as e:
            log.error(f"❌ Order execution failed: {e}")

    async def _execute_open(self, symbol: str, side: str, qty: float, stop: float, tp: float):
        """Place Market entry + SL + TP on Binance Futures."""
        
        # 1. Main Market Order
        main_side = 'BUY' if side == 'LONG' else 'SELL'
        log.info(f"➜ Submitting {main_side} MARKET for {qty} {symbol}")
        
        # To handle floating point issues on Binance
        qty_str = f"{qty:.3f}" if 'BTC' in symbol else f"{qty:.2f}"
        
        main_order = await self.client.futures_create_order(
            symbol=symbol,
            side=main_side,
            type='MARKET',
            quantity=qty_str
        )
        log.info(f"✅ Market Order Filled: {main_order['orderId']}")

        # Opposing side for exit orders
        exit_side = 'SELL' if side == 'LONG' else 'BUY'

        # 2. Stop Loss (STOP_MARKET)
        if stop and stop > 0:
            stop_price = round(stop, 1)
            log.info(f"➜ Submitting STOP_MARKET for {symbol} at {stop_price}")
            await self.client.futures_create_order(
                symbol=symbol,
                side=exit_side,
                type='STOP_MARKET',
                stopPrice=stop_price,
                closePosition='true',
                timeInForce='GTC'
            )
            
        # 3. Take Profit (TAKE_PROFIT_MARKET)
        if tp and tp > 0:
            tp_price = round(tp, 1)
            log.info(f"➜ Submitting TAKE_PROFIT_MARKET for {symbol} at {tp_price}")
            await self.client.futures_create_order(
                symbol=symbol,
                side=exit_side,
                type='TAKE_PROFIT_MARKET',
                stopPrice=tp_price,
                closePosition='true',
                timeInForce='GTC'
            )
            
    async def _execute_close(self, symbol: str, side: str, qty: float):
        """Close existing position and cancel pending SL/TP."""
        exit_side = 'SELL' if side == 'LONG' else 'BUY'
        qty_str = f"{qty:.3f}" if 'BTC' in symbol else f"{qty:.2f}"
        
        # 1. Close position via MARKET
        log.info(f"➜ Closing {side} position via {exit_side} MARKET {qty} {symbol}")
        await self.client.futures_create_order(
            symbol=symbol,
            side=exit_side,
            type='MARKET',
            quantity=qty_str,
            reduceOnly='true'
        )
        
        # 2. Cancel all open orders (SL/TP) for this symbol
        await self.client.futures_cancel_all_open_orders(symbol=symbol)
        log.info(f"✅ Position closed and standing orders cancelled for {symbol}")
