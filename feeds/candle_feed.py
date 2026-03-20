"""
feeds/candle_feed.py
Multi-Timeframe OHLCV Aggregator — Phase 2

Monitors the live 1m kline from WebSocketManager,
and when it closes, it queries ccxt (or maintains internally)
the historical 1m, 5m, 15m, 1h, and 4h DataFrames and pushes to Redis.
"""

import asyncio
import logging
import pandas as pd
from core.state_manager import StateManager
from config import get_exchange

log = logging.getLogger("CandleFeed")

class CandleFeedManager:
    def __init__(self, symbols: list, timeframes: list, state: StateManager):
        self.symbols = symbols
        self.timeframes = timeframes  # e.g. ["1m", "5m", "15m", "1h", "4h"]
        self.state = state
        self.exchange = get_exchange()
        self.running = False

    async def run_forever(self):
        self.running = True
        log.info(f"🕯️ Starting CandleFeed aggregator for {self.timeframes}")
        
        # 1. Initial Data Fetch (Bootstrap)
        await self._bootstrap_all()

        # 2. Polling loop: Watch `live_kline:1m:SYMBOL`
        # Because Binance sends `x: true` when a 1m candle closes
        last_closed = {sym: 0 for sym in self.symbols}
        
        while self.running:
            try:
                for symbol in self.symbols:
                    kline = await self.state.get(f"live_kline:1m:{symbol}")
                    if kline and kline.get('closed', False):
                        ts = kline['timestamp']
                        if ts > last_closed[symbol]:
                            last_closed[symbol] = ts
                            # Realistically, we append to df, but for simplicity/safety
                            # we can refetch the tail from CCXT, or build from 1m.
                            # Since CCXT fetch takes 100ms and we only do it every 60s:
                            log.debug(f"[{symbol}] 1m candle closed, updating DataFrames...")
                            await self._update_symbol_timeframes(symbol)
                
                await asyncio.sleep(1)
            except asyncio.CancelledError:
                break
            except Exception as e:
                log.error(f"CandleFeed loop error: {e}")
                await asyncio.sleep(5)

    async def _bootstrap_all(self):
        """Fetch historical data on startup."""
        for symbol in self.symbols:
            await self._update_symbol_timeframes(symbol, limit=500)
            
    async def _update_symbol_timeframes(self, symbol: str, limit: int = 100):
        """Fetch all required timeframes via ccxt and store in Redis."""
        # Note: In a true ultra-low latency system, you'd aggregate the 1m bars 
        # in memory. CCXT fetch overhead is ~200ms which is fine for 1m strategies.
        for tf in self.timeframes:
            try:
                # CCXT is synchronous, so we run it in thread pool to not block asyncio loop
                loop = asyncio.get_event_loop()
                raw = await loop.run_in_executor(
                    None, 
                    lambda: self.exchange.fetch_ohlcv(symbol, tf, limit=limit)
                )
                df = pd.DataFrame(raw, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
                
                # Store in Redis
                await self.state.set_df(f"ohlcv:{tf}:{symbol}", df)
                
            except Exception as e:
                log.error(f"Failed to fetch {tf} for {symbol}: {e}")
                
        # Fire event that new candles are ready
        await self.state.publish(f"candles_updated:{symbol}", "1")
        
    def stop(self):
        self.running = False
