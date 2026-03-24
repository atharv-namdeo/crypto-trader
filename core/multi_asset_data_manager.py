import asyncio
import logging
import pandas as pd
from typing import List, Dict, Optional
from config import SYMBOLS, TIMEFRAMES
from core.state_manager import StateManager

log = logging.getLogger("MultiAssetDataManager")

class MultiAssetDataManager:
    """
    Optimized data fetcher for multi-asset trading.
    Handles parallel fetching of candle data for 15+ symbols and 5+ timeframes.
    Caches data in Redis for shared access between strategy and ML layers.
    """

    def __init__(self, exchange, state: StateManager):
        self.exchange = exchange
        self.state = state
        self.symbols = SYMBOLS
        # Handle dict vs list for backward/forward compatibility
        if isinstance(TIMEFRAMES, dict):
            self.timeframes = list(set(TIMEFRAMES.values()))
        else:
            self.timeframes = TIMEFRAMES
        self.semaphore = asyncio.Semaphore(10)  # Limit concurrent API calls
        self.last_fetch = {}  # Track last update per symbol/timeframe

    async def fetch_all_candles(self, limit: int = 100):
        """
        Refresh all OHLCV data for all symbols and timeframes.
        Uses asyncio.gather for massive parallelism.
        """
        log.info(f"🔄 Refreshing data for {len(self.symbols)} assets across {len(self.timeframes)} timeframes...")
        
        tasks = []
        for symbol in self.symbols:
            tasks.append(self._refresh_symbol_data(symbol, limit))
        
        await asyncio.gather(*tasks)
        log.info(f"✅ All assets refreshed.")

    async def _refresh_symbol_data(self, symbol: str, limit: int):
        """Refresh all timeframes for a single symbol."""
        tasks = []
        for tf in self.timeframes:
            tasks.append(self._fetch_and_store(symbol, tf, limit))
        await asyncio.gather(*tasks)

    async def _fetch_and_store(self, symbol: str, tf: str, limit: int):
        """Single OHLCV fetch with rate limiting and Redis storage."""
        async with self.semaphore:
            try:
                # Fetch from exchange
                candles = await self.exchange.fetch_ohlcv(symbol, timeframe=tf, limit=limit)
                if not candles:
                    return

                # Convert to DataFrame
                df = pd.DataFrame(candles, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
                
                # Store in Redis via StateManager
                redis_key = f"ohlcv:{tf}:{symbol}"
                await self.state.set_df(redis_key, df, expire_seconds=3600)  # Cache for 1 hour
                
                # Update last fetch time
                self.last_fetch[f"{symbol}:{tf}"] = pd.Timestamp.now()
            except Exception as e:
                log.error(f"Error fetching {symbol} {tf}: {e}")

    async def get_candles(self, symbol: str, timeframe: str, n: int = 100) -> Optional[pd.DataFrame]:
        """Interface for strategies to get cached candle data."""
        redis_key = f"ohlcv:{timeframe}:{symbol}"
        return await self.state.get_df(redis_key, n=n)

    async def run_loop(self, interval_seconds: int = 60):
        """Background task to keep data fresh."""
        while True:
            try:
                await self.fetch_all_candles()
            except Exception as e:
                log.error(f"Error in MultiAssetDataManager loop: {e}")
            await asyncio.sleep(interval_seconds)
