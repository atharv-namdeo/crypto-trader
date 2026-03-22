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
    def __init__(self, state: StateManager):
        self.state = state
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
        qty = round(req.get('qty', 0), 5)
        price = req.get('price', 0)

        if self.dry_run:
            log.info(f"📝 PAPER TRADE: {side} {market_sym} qty={qty}")
            # Log signal even in dry run for dashboard visibility
            try:
                from datetime import datetime
                signal = {
                    'time': datetime.utcnow().timestamp(),
                    'price': price,
                    'type': side,
                    'action': action,
                    'strategy': req.get('strategy', 'UNKNOWN'),
                    'pnl': 0
                }
                await self.state.redis.lpush('signals:history', json.dumps(signal))
                await self.state.redis.ltrim('signals:history', 0, 99)
            except: pass
            return True

        try:
            if action == 'OPEN':
                await self._execute_open(market_sym, side, qty, price, req.get('stop'), req.get('tp'))
                # Log signal for chart
                try:
                    from datetime import datetime
                    signal = {
                        'time': datetime.utcnow().timestamp(),
                        'price': price,
                        'type': side,
                        'action': 'OPEN',
                        'strategy': req.get('strategy', 'UNKNOWN'),
                        'pnl': 0
                    }
                    await self.state.redis.lpush('signals:history', json.dumps(signal))
                    await self.state.redis.ltrim('signals:history', 0, 99)
                except: pass
            elif action == 'CLOSE':
                await self._execute_close(market_sym, side, qty)
            return True
            
        except BinanceAPIException as e:
            log.error(f"[TESTNET ERROR] {e.message} — retrying in 10s")
            return False
        except Exception as e:
            log.error(f"[TESTNET ERROR] {e} — retrying in 10s")
            return False

    async def _execute_open(self, symbol: str, side: str, qty: float, price: float, stop: float, tp: float):
        main_side = 'BUY' if side == 'LONG' else 'SELL'
        qty_str = f"{qty:.3f}" if 'BTC' in symbol else f"{qty:.2f}"
        
        log.info(f"[TESTNET ORDER] OPEN {side} {symbol} qty={qty_str} @ {price}")
        
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
        
        close_order = await self.client.futures_create_order(
            symbol=symbol,
            side=exit_side,
            type='MARKET',
            quantity=qty_str,
            reduceOnly='true'
        )
        log.info(f"[TESTNET FILLED] order_id={close_order['orderId']}")
        
        await self.client.futures_cancel_all_open_orders(symbol=symbol)
