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
import aiohttp
from core.state_manager import StateManager

log = logging.getLogger("CandleFeed")

class CandleFeedManager:
    def __init__(self, symbols: list, timeframes: list, state: StateManager, max_concurrent: int = 10):
        self.symbols = symbols
        self.timeframes = timeframes  
        self.state = state
        self.running = False
        self.semaphore = asyncio.Semaphore(max_concurrent)

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
        """Fetch historical data on startup — pre-seed 200+ candles for all symbols in parallel."""
        log.info(f"📊 Pre-seeding candle history for {len(self.symbols)} symbols...")
        tasks = [self._update_symbol_timeframes(symbol, limit=500) for symbol in self.symbols]
        await asyncio.gather(*tasks)
        log.info("✅ All symbols bootstrapped.")
            
    async def _update_symbol_timeframes(self, symbol: str, limit: int = 100):
        """Update all timeframes for a single symbol, using Demo API if testnet is active."""
        from config import settings
        
        async with self.semaphore:
            # Use Demo API for testnet to bypass geo-restrictions
            if settings.BINANCE_TESTNET:
                base_url = "https://demo-api.binance.com/api/v3/klines"
            else:
                base_url = "https://fapi.binance.com/fapi/v1/klines"

            session = aiohttp.ClientSession()
            try:
                for tf in self.timeframes:
                    try:
                        market_sym = symbol.replace('/', '').upper()
                        url = f"{base_url}?symbol={market_sym}&interval={tf}&limit={limit}"
                        
                        async with session.get(url, timeout=10) as response:
                            if response.status != 200:
                                log.error(f"Binance API error {response.status} for {symbol} {tf}")
                                continue
                            raw = await response.json()
                        
                        data = []
                        for k in raw:
                            data.append({
                                'timestamp': int(k[0]),
                                'open':   float(k[1]),
                                'high':   float(k[2]),
                                'low':    float(k[3]),
                                'close':  float(k[4]),
                                'volume': float(k[5]),
                            })
                        df = pd.DataFrame(data)
                        await self.state.set_df(f"ohlcv:{tf}:{symbol}", df)
                        
                    except Exception as e:
                        log.error(f"Failed to fetch {tf} for {symbol}: {e}")
            finally:
                await session.close()
        
        await self.state.publish(f"candles_updated:{symbol}", "1")
        
    def stop(self):
        self.running = False
