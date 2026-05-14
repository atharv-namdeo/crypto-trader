"""
execution/order_engine.py
Binance Futures Async Order Engine — Phase 4
"""

import os
import json
import asyncio
import logging
import traceback
from binance import AsyncClient
from binance.exceptions import BinanceAPIException
from core.state_manager import StateManager
from config import SYMBOLS

log = logging.getLogger("OrderEngine")

class OrderEngine:
    def __init__(self, state: StateManager, portfolio_risk=None):
        from config import settings
        from core.telegram_notifier import TelegramNotifier
        self.state = state
        self.portfolio_risk = portfolio_risk
        self.running = False
        self.use_testnet = settings.BINANCE_TESTNET
        self.dry_run = settings.DRY_RUN
        self.telegram = TelegramNotifier()
        
        # Consistent key hierarchy (Demo -> Test -> Real)
        self.api_key = (
            settings.BINANCE_DEMO_API_KEY or 
            settings.BINANCE_TEST_API_KEY or 
            settings.BINANCE_API_KEY
        )
        self.api_secret = (
            settings.BINANCE_DEMO_API_SECRET or 
            settings.BINANCE_TEST_API_SECRET or 
            settings.BINANCE_API_SECRET
        )
        self.client: AsyncClient = None

    async def init_client(self):
        """Initialize AsyncClient and configure account (Non-blocking)."""
        if not self.api_key or not self.api_secret:
            log.warning("⚠️ No Binance API keys found. Order Engine will skip execution.")
            return

        try:
            self.client = await AsyncClient.create(
                api_key=self.api_key,
                api_secret=self.api_secret,
                testnet=self.use_testnet
            )
            
            if self.use_testnet:
                # Optimized endpoint for Demo/Testnet
                self.client.API_URL = 'https://testnet.binancefuture.com/fapi'
                self.client.BASE_URL = 'https://testnet.binancefuture.com'
                log.info("✅ Order Engine connected to Binance Testnet")
            
            # Sync history on startup (Optional)
            asyncio.create_task(self.sync_historical_trades())
            
        except Exception as e:
            log.error(f"❌ Order Engine API connection FAILED: {e}")
            log.warning("Continuing in DEGRADED MODE (Order execution disabled)")
            self.client = None

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
        if not self.client:
            log.warning(f"⚠️ Skipping order for {symbol} - Order Engine in DEGRADED MODE (Uninitialized)")
            return True # Toss request to avoid loop
            
        market_sym = symbol.replace('/', '').upper()
        action = req.get('action')
        side = req.get('side')
        qty = float(req.get('qty', 0))
        price = float(req.get('price', 0))

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
        except BinanceAPIException as be:
            log.error(f"❌ [BINANCE ERROR] Code: {be.code} | Msg: {be.message}")
            return False
        except Exception as e:
            log.error(f"🔥 Process Order General Error on {symbol}: {e}")
            log.error(traceback.format_exc())
            return False

    async def sync_historical_trades(self):
        """Fetch past trades from Binance to populate Redis history if empty."""
        try:
            log.info("🔄 Syncing historical trades from Binance...")
            # Check if we already have history to avoid duplicates
            existing = await self.state.redis.llen('trade:history')
            if existing > 0:
                log.info(f"📁 Trade history already has {existing} items, skipping sync.")
                return

            all_synced_trades = []
            for symbol in SYMBOLS[:10]: # Sync top 10 symbols to avoid rate limits on startup
                market_sym = symbol.replace('/', '').upper()
                orders = await self.client.futures_get_all_orders(symbol=market_sym, limit=20)
                
                for o in orders:
                    if o['status'] == 'FILLED':
                        trade = {
                            'strategy': 'LEGACY',
                            'symbol': symbol,
                            'side': o['side'],
                            'entry': float(o['avgPrice'] or o['price']),
                            'exit': float(o['avgPrice'] or o['price']),
                            'qty': float(o['executedQty']),
                            'pnl': 0.0, # Cannot reliably compute PnL from orders alone without matching
                            'reason': 'SYNCED',
                            'time': datetime.fromtimestamp(o['updateTime']/1000).isoformat()
                        }
                        all_synced_trades.append(trade)
            
            # Sort by time and push to Redis
            all_synced_trades.sort(key=lambda x: x['time'])
            for t in all_synced_trades:
                await self.state.redis.rpush('trade:history', json.dumps(t))
            
            log.info(f"✅ Synced {len(all_synced_trades)} historical trades.")
        except Exception as e:
            log.error(f"❌ History sync failed: {e}")

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
        
        if self.dry_run:
            log.info(f"🧪 [DRY RUN] Simulating {main_side} {symbol} qty={qty}")
            main_order = {
                'orderId': f'DRY_{int(datetime.utcnow().timestamp())}',
                'updateTime': int(datetime.utcnow().timestamp() * 1000),
                'avgPrice': price
            }
        else:
            qty_str = f"{qty}"
            log.info(f"⚡ [SOR] Attempting LIMIT order for {symbol} to save fees...")
            try:
                limit_order = await self.client.futures_create_order(
                    symbol=symbol, side=main_side, type='LIMIT', timeInForce='GTX', quantity=qty_str, price=str(price))
                for _ in range(5):
                    await asyncio.sleep(1)
                    status = await self.client.futures_get_order(symbol=symbol, orderId=limit_order['orderId'])
                    if status['status'] == 'FILLED':
                        main_order = status; break
                else:
                    await self.client.futures_cancel_order(symbol=symbol, orderId=limit_order['orderId'])
                    main_order = await self.client.futures_create_order(symbol=symbol, side=main_side, type='MARKET', quantity=qty_str)
            except:
                main_order = await self.client.futures_create_order(symbol=symbol, side=main_side, type='MARKET', quantity=qty_str)

        # Telegram Alert (Phase 11 Activation)
        await self.telegram.trade_opened(
            strategy=strategy, symbol=symbol, side=side, entry=price,
            qty=qty, stop=stop, tp=tp, conviction=0.85 
        )

        # Sync to Firebase
        self.state.firebase.set(f"trading/orders/{main_order['orderId']}", {
            "symbol": symbol, "type": "MARKET", "side": main_side, "quantity": qty,
            "price": float(main_order.get('avgPrice', price)), "status": "FILLED",
            "timestamp": int(main_order['updateTime']), "binance_order_id": main_order['orderId'], "strategy": strategy
        })

        if not self.dry_run:
            exit_side = 'SELL' if side == 'LONG' else 'BUY'
            if stop and stop > 0:
                await self.client.futures_create_order(symbol=symbol, side=exit_side, type='STOP_MARKET', stopPrice=round(stop, 1), closePosition='true', timeInForce='GTC')
            if tp and tp > 0:
                await self.client.futures_create_order(symbol=symbol, side=exit_side, type='TAKE_PROFIT_MARKET', stopPrice=round(tp, 1), closePosition='true', timeInForce='GTC')

    async def _execute_close(self, symbol: str, side: str, qty: float):
        exit_side = 'SELL' if side == 'LONG' else 'BUY'
        
        if self.dry_run:
            log.info(f"🧪 [DRY RUN] Simulating CLOSE {side} {symbol}")
            return

        qty_str = f"{qty:.3f}" if 'BTC' in symbol else f"{qty:.2f}"
        log.info(f"[TESTNET ORDER] CLOSE {side} {symbol} qty={qty_str}")
        
        try:
            # Telegram Alert (Phase 11 Activation)
            price = await self.state.get_float(f"price:{symbol}")
            await self.telegram.trade_closed(
                strategy="ENSEMBLE", symbol=symbol, side=side,
                entry=0.0, exit_price=price, qty=qty, pnl=0.0, reason="Signal Close", duration="LIVE"
            )

            close_order = await self.client.futures_create_order(
                symbol=symbol,
                side=exit_side,
                type='MARKET',
                quantity=qty_str,
                reduceOnly='true'
            )
            log.info(f"[TESTNET FILLED] order_id={close_order['orderId']}")
            await self.client.futures_cancel_all_open_orders(symbol=symbol)
        except Exception as e:
            log.warning(f"⚠️ Close failed for {symbol}: {e}")

    async def get_active_orders(self) -> list:
        """Fetch all open orders from Binance Futures."""
        try:
            if not self.client: await self.init_client()
            orders = await self.client.futures_get_open_orders()
            return [{
                "symbol": o['symbol'],
                "id": o['orderId'],
                "side": o['side'],
                "type": o['type'],
                "price": float(o['price']),
                "qty": float(o['origQty']),
                "time": o['updateTime']
            } for o in orders]
        except Exception as e:
            log.error(f"Error fetching active orders: {e}")
            return []
