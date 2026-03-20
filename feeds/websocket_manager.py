"""
feeds/websocket_manager.py
Binance WebSocket Feed Manager — Phase 2

Connects to Binance WS, streams live trades and order book data,
and pushes directly into Redis for ultra-low latency consumption by the signal engine.
"""

import os
import json
import asyncio
import logging
import websockets
from core.state_manager import StateManager
from config import SYMBOLS, get_exchange

log = logging.getLogger("WebSocketFeed")

class WebSocketManager:
    def __init__(self, symbols: list, state: StateManager):
        self.symbols = symbols
        self.state = state
        # We determine testnet based on exchange config or env
        self.use_testnet = os.getenv("USE_TESTNET", "True").lower() in ('true', '1')
        
        # Binance URLs
        if self.use_testnet:
            self.base_url = "wss://stream.binancefuture.com/ws"
        else:
            self.base_url = "wss://fstream.binance.com/ws"

        self.running = False
        self._ws = None

    def _get_stream_url(self):
        """Build the combined stream URL for all requested symbols and streams."""
        streams = []
        for sym in self.symbols:
            # Binance WS requires lowercase symbol, e.g., btcusdt
            s = sym.lower().replace('/', '')
            streams.append(f"{s}@trade")          # Every trade execution
            streams.append(f"{s}@depth10@100ms")  # Top 10 levels of orderbook every 100ms
            streams.append(f"{s}@kline_1m")       # Live 1m candles for open/high/low updates
        
        joined = "/".join(streams)
        return f"{self.base_url.replace('/ws', '/stream')}?streams={joined}"

    async def run_forever(self):
        """Maintain connection and handle auto-reconnects."""
        self.running = True
        url = self._get_stream_url()
        log.info(f"🔗 Starting WebSocket connection to {url}")
        
        while self.running:
            try:
                async with websockets.connect(url, ping_interval=20, ping_timeout=20) as ws:
                    self._ws = ws
                    log.info("✅ WebSocket connected successfully")
                    await self._listen(ws)
            except asyncio.CancelledError:
                log.info("WebSocket feed cancelled")
                break
            except Exception as e:
                log.error(f"❌ WebSocket disconnected: {e}. Reconnecting in 5s...")
                await asyncio.sleep(5)

    async def _listen(self, ws):
        """Listen to incoming WS messages and route to Redis."""
        while self.running:
            try:
                msg_str = await ws.recv()
                msg = json.loads(msg_str)
                await self._handle_message(msg)
            except websockets.exceptions.ConnectionClosed:
                log.warning("WS connection closed by upstream")
                break
            except Exception as e:
                log.error(f"WS listen error: {e}")
                
    async def _handle_message(self, msg: dict):
        """Parse message and update Redis state."""
        if 'stream' not in msg or 'data' not in msg:
            return
            
        stream_name = msg['stream']
        data = msg['data']
        
        # Extract symbol
        # stream_name is like btcusdt@trade
        parts = stream_name.split('@')
        raw_sym = parts[0].upper()
        # Ensure it matches our SYMBOLS format (e.g. BTCUSDT)
        symbol = next((s for s in self.symbols if s.replace('/', '') == raw_sym), raw_sym)
        event_type = parts[1] if len(parts) > 1 else ""

        if event_type == 'trade':
            # { "e": "trade", "p": "69000.5", "q": "0.1", "m": true }
            await self._process_trade(symbol, data)
            
        elif event_type.startswith('depth'):
            # { "lastUpdateId": ..., "bids": [["69000","0.1"]], "asks": [...] }
            await self._process_orderbook(symbol, data)
            
        elif event_type.startswith('kline'):
            # { "e": "kline", "k": { "o": "...", "h": "...", "l": "...", "c": "...", "v": "...", "x": false } }
            await self._process_kline(symbol, data)

    async def _process_trade(self, symbol: str, data: dict):
        """Process real-time trade execute. Maintain rolling tape of last 60s."""
        trade = {
            'price': float(data['p']),
            'qty': float(data['q']),
            'side': 'sell' if data.get('m', False) else 'buy',  # m=True means buyer was maker → sell hit the bid
            'time': data.get('T', asyncio.get_event_loop().time() * 1000)
        }
        
        # 1. Update latest price
        await self.state.set(f"price:{symbol}", trade['price'])
        
        # 2. Append to rolling tape directly in Redis
        # Using a Redis list and LTRIM to keep only last ~500 trades
        key = f"tape:{symbol}"
        try:
            trade_str = json.dumps(trade)
            await self.state.redis.lpush(key, trade_str)
            await self.state.redis.ltrim(key, 0, 500)
        except Exception:
            pass

    async def _process_orderbook(self, symbol: str, data: dict):
        """Process L2 orderbook snapshot (top 10 levels)."""
        bids = [[float(p), float(q)] for p, q in data.get('bids', [])]
        asks = [[float(p), float(q)] for p, q in data.get('asks', [])]
        
        ob = {'bids': bids, 'asks': asks, 'time': asyncio.get_event_loop().time()}
        await self.state.set(f"orderbook:{symbol}", ob, expire_seconds=60)

    async def _process_kline(self, symbol: str, data: dict):
        """Live candle updates for the current 1m bar."""
        k = data.get('k', {})
        candle = {
            'timestamp': int(k.get('t', 0)),
            'open': float(k.get('o', 0)),
            'high': float(k.get('h', 0)),
            'low': float(k.get('l', 0)),
            'close': float(k.get('c', 0)),
            'volume': float(k.get('v', 0)),
            'closed': k.get('x', False)
        }
        await self.state.set(f"live_kline:1m:{symbol}", candle, expire_seconds=120)

    def stop(self):
        self.running = False
        if self._ws:
            asyncio.create_task(self._ws.close())
