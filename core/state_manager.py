"""
core/state_manager.py
Async Redis Interface Layer — Phase 2

All processes (feeds, signals, ml, execution) communicate through Redis.
This allows them to run concurrently without blocking.
"""

import json
import logging
import asyncio
import pandas as pd
from typing import Any, Optional
import os
from config import REDIS_URL

log = logging.getLogger("StateManager")

class StateManager:
    """Manages shared state via Redis with JSON serialization."""
    
    def __init__(self, redis_url: str = None):
        self.url = redis_url or os.getenv("REDIS_URL", "redis://localhost:6379")
        self.redis: Optional[redis.Redis] = None
        self._pubsub: Optional[redis.client.PubSub] = None

    async def connect(self):
        """Establish Redis connection."""
        try:
            import redis.asyncio as redis
            self.redis = redis.from_url(self.url, decode_responses=True)
            await self.redis.ping()
            log.info(f"✅ Connected to Redis at {self.url}")
        except Exception as e:
            log.critical(f"❌ Redis connection failed: {e}")
            raise

    async def close(self):
        """Close Redis connection."""
        if self.redis:
            await self.redis.close()

    # ── KEY/VALUE STORE ───────────────────────────────────────────────────

    async def set(self, key: str, value: Any, expire_seconds: int = None):
        """Store JSON-serializable value in Redis."""
        try:
            val_str = json.dumps(value)
            await self.redis.set(key, val_str, ex=expire_seconds)
        except Exception as e:
            log.error(f"Redis set error on {key}: {e}")

    async def get(self, key: str) -> Optional[Any]:
        """Retrieve and deserialize JSON value from Redis."""
        try:
            val_str = await self.redis.get(key)
            if val_str:
                return json.loads(val_str)
            return None
        except Exception as e:
            log.error(f"Redis get error on {key}: {e}")
            return None

    async def get_float(self, key: str) -> Optional[float]:
        """Optimized getter for float values (prices, scores)."""
        val = await self.redis.get(key)
        if val is not None:
            try:
                return float(val)
            except ValueError:
                return None
        return None

    # ── PANDAS DATAFRAME HELPERS ──────────────────────────────────────────

    async def set_df(self, key: str, df: pd.DataFrame, expire_seconds: int = None):
        """Store Pandas DataFrame as JSON string (records orientation)."""
        try:
            # Drop datetime index to default numeric if needed, then to_dict
            df_json = df.to_dict(orient='records')
            await self.set(key, df_json, expire_seconds)
        except Exception as e:
            log.error(f"Redis set_df error on {key}: {e}")

    async def get_df(self, key: str, n: int = None) -> Optional[pd.DataFrame]:
        """
        Retrieve JSON and convert to DataFrame. 
        If n is specified, returns only the last n rows.
        """
        data_list = await self.get(key)
        if data_list is None or not isinstance(data_list, list):
            return None
            
        try:
            # If n specified, only convert the tail for performance
            if n and len(data_list) > n:
                data_list = data_list[-n:]
                
            df = pd.DataFrame(data_list)
            # Standardize datetime parsing if timestamp column exists
            if 'timestamp' in df.columns:
                df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            return df
        except Exception as e:
            log.error(f"Redis get_df error on {key}: {e}")
            return None

    async def get_series(self, key: str, n: int = None) -> Optional[pd.Series]:
        """Retrieve specialized time series (e.g. just a list of floats) as pandas Series."""
        data_list = await self.get(key)
        if data_list is None or not isinstance(data_list, list):
            return None
        try:
            if n and len(data_list) > n:
                data_list = data_list[-n:]
            return pd.Series(data_list)
        except Exception as e:
            return None

    # ── POSITION AGGREGATION ──────────────────────────────────────────────

    async def set_position(self, symbol: str, position: dict):
        import json
        await self.redis.set(f"position:{symbol}", json.dumps(position))

    async def get_position(self, symbol: str):
        import json
        data = await self.redis.get(f"position:{symbol}")
        return json.loads(data) if data else None

    async def get_all_positions(self) -> dict:
        """Fetch all keys matching 'position:*' and return dict of {symbol: pos_dict}"""
        positions = {}
        try:
            keys = await self.redis.keys("position:*")
            if not keys:
                return positions
                
            # Pipeline for faster multiple gets
            pipe = self.redis.pipeline()
            for k in keys:
                pipe.get(k)
            values = await pipe.execute()
            
            for key, val_str in zip(keys, values):
                if val_str:
                    symbol = key.split(":")[1]
                    positions[symbol] = json.loads(val_str)
                    
            return positions
        except Exception as e:
            log.error(f"Redis get_all_positions error: {e}")
            return {}

    # ── PUB / SUB ─────────────────────────────────────────────────────────

    async def publish(self, channel: str, message: Any):
        """Publish JSON payload to a channel."""
        try:
            msg_str = json.dumps(message)
            await self.redis.publish(channel, msg_str)
        except Exception as e:
            log.error(f"Redis publish error on {channel}: {e}")

    async def subscribe(self, channel: str):
        """Return an async listener for a specific channel."""
        try:
            if not self._pubsub:
                self._pubsub = self.redis.pubsub()
            await self._pubsub.subscribe(channel)
            return self._pubsub
        except Exception as e:
            log.error(f"Redis subscribe error on {channel}: {e}")
            return None
