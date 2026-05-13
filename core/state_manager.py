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
import gzip
import base64
from config import REDIS_URL
# --- GRACEFUL FALLBACK: FirebaseManager ---
try:
    from core.firebase_manager import FirebaseManager
except ImportError:
    log.warning("⚠️ FirebaseManager not found - using stub for dashboard visibility")
    class FirebaseManager:
        def __init__(self, *args, **kwargs): pass
        def update(self, *args, **kwargs): pass
        def set(self, *args, **kwargs): pass
        def push(self, *args, **kwargs): pass
        def get(self, *args, **kwargs): return None
        def delete(self, *args, **kwargs): pass

log = logging.getLogger("StateManager")

class StateManager:
    """Manages shared state via Redis with JSON serialization."""
    
    def __init__(self, redis_url: str = None):
        self.url = redis_url or os.getenv("REDIS_URL", "redis://localhost:6379")
        self.redis: Optional[Any] = None
        self._pubsub: Optional[Any] = None
        self.firebase = FirebaseManager()

    async def connect(self):
        """Establish Redis connection with retry logic."""
        import redis.asyncio as redis_lib
        max_retries = 2 # Reduced for faster local development
        for attempt in range(max_retries):
            try:
                self.redis = redis_lib.from_url(self.url, decode_responses=True)
                await asyncio.wait_for(self.redis.ping(), timeout=2.0)
                log.info(f"✅ Connected to Redis at {self.url}")
                return
            except Exception as e:
                log.warning(f"⚠️ Redis connection attempt {attempt+1}/{max_retries} failed: {e}")
                if attempt == max_retries - 1:
                    log.warning("⚠️ Falling back to In-Memory Mock Redis (State will NOT persist!)")
                    self.redis = MemoryMock()
                    return
                await asyncio.sleep(1)

    async def close(self):
        """Close Redis connection."""
        if self.redis:
            await self.redis.close()

    # ── KEY/VALUE STORE ───────────────────────────────────────────────────

    async def set(self, key: str, value: Any, expire_seconds: int = None, compress: bool = False):
        """Store JSON-serializable value in Redis, optionally with GZIP compression."""
        try:
            val_str = json.dumps(value)
            if compress:
                data_compressed = gzip.compress(val_str.encode())
                # Use base64 if we want to store it in a decode_responses=True connection
                # or better, use a separate connection for binary data. 
                # For now, let's just store as string if possible or hex.
                # Actually, decode_responses=True will fail with binary.
                # I'll use base64 for compatibility with the current setup.
                val_str = base64.b64encode(data_compressed).decode()
                key = f"gz:{key}" # Prefix compressed keys
            
            await self.redis.set(key, val_str, ex=expire_seconds)
            
            # --- MISSION CRITICAL: FIREBASE MIRRORING ---
            await self._mirror_to_firebase(key, value)
            
        except Exception as e:
            log.error(f"Redis set error on {key}: {e}")

    async def _mirror_to_firebase(self, key: str, value: Any):
        """Sync high-level state to Firebase for Cloud Dashboard visibility."""
        try:
            # 1. Price & Confidence Updates
            if key.startswith("price:"):
                symbol = key.split(":")[1]
                # Async get confidence if available
                conf_val = await self.redis.get(f"ensemble_confidence:{symbol}")
                conf = float(conf_val) if conf_val else 0
                
                self.firebase.update(f"market/prices/{symbol}", {
                    "current_price": value,
                    "confidence": conf * 100, # Percentage for dashboard
                    "timestamp": int(asyncio.get_event_loop().time() * 1000)
                })
            
            # 2. Strategy Signals
            elif key.startswith("ml_signal:") or key.startswith("ensemble_signal:"):
                symbol = key.split(":")[1]
                self.firebase.set(f"trading/signals/{symbol}", value)
            
            # 3. Fuzzy Scores (Advanced Signals)
            elif key.startswith("fuzzy:"):
                symbol = key.split(":")[1]
                self.firebase.set(f"market/fuzzy/{symbol}", value)
            
            # 4. Engine Status
            elif key == "engine:status":
                self.firebase.set("status/label", value)
            elif key == "engine:exchange":
                self.firebase.set("status/exchange", value)
                
            # 5. Portfolio Metrics
            elif key.startswith("portfolio:"):
                metric_name = key.split(":")[1]
                self.firebase.set(f"analytics/performance/summary/{metric_name}", value)
            
            # 6. Strategy Stats
            elif key.startswith("stats:"):
                parts = key.split(":")
                if len(parts) >= 3:
                    strategy = parts[1]
                    metric = parts[2]
                    self.firebase.set(f"trading/strategies/{strategy}/{metric}", value)
            
            # 7. Aggregated Positions
            elif key == "positions:active":
                self.firebase.set("trading/positions_active", value)
                
            # 8. Active Orders
            elif key == "orders:active":
                self.firebase.set("trading/orders_active", value)

        except Exception as e:
            log.debug(f"Firebase mirror skip for {key}: {e}")

    async def get(self, key: str) -> Optional[Any]:
        """Retrieve and deserialize JSON value from Redis, handling GZIP if prefixed."""
        try:
            is_compressed = key.startswith("gz:")
            val_str = await self.redis.get(key)
            if not val_str and not is_compressed:
                # Try with gz: prefix just in case
                val_str = await self.redis.get(f"gz:{key}")
                if val_str: is_compressed = True
            
            if val_str:
                if is_compressed:
                    data_compressed = base64.b64decode(val_str.encode())
                    val_str = gzip.decompress(data_compressed).decode()
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
            except (ValueError, TypeError):
                return None
        return None

    # ── PANDAS DATAFRAME HELPERS ──────────────────────────────────────────

    async def set_df(self, key: str, df: pd.DataFrame, expire_seconds: int = 3600):
        """Store Pandas DataFrame with compression and default 1hr TTL."""
        try:
            df_json = df.to_dict(orient='records')
            await self.set(key, df_json, expire_seconds, compress=True)
        except Exception as e:
            log.error(f"Redis set_df error on {key}: {e}")

    async def get_df(self, key: str, n: int = None) -> Optional[pd.DataFrame]:
        data_list = await self.get(key)
        if data_list is None or not isinstance(data_list, list):
            return None
            
        try:
            if n and len(data_list) > n:
                data_list = data_list[-n:]
            df = pd.DataFrame(data_list)
            if 'timestamp' in df.columns:
                df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            return df
        except Exception as e:
            log.error(f"Redis get_df error on {key}: {e}")
            return None

    async def get_series(self, key: str, n: int = None) -> Optional[pd.Series]:
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
        await self.redis.set(f"position:{symbol}", json.dumps(position))
        # Sync position to Firebase
        self.firebase.set(f"trading/positions/{symbol}", position)

    async def get_position(self, symbol: str):
        data = await self.redis.get(f"position:{symbol}")
        return json.loads(data) if data else None

    async def get_all_positions(self) -> dict:
        positions = {}
        try:
            keys = await self.redis.keys("position:*")
            if not keys: return positions
            pipe = self.redis.pipeline()
            for k in keys: pipe.get(k)
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
        try:
            msg_str = json.dumps(message)
            await self.redis.publish(channel, msg_str)
        except Exception as e:
            log.error(f"Redis publish error on {channel}: {e}")

    async def subscribe(self, channel: str):
        try:
            if not self._pubsub:
                self._pubsub = self.redis.pubsub()
            await self._pubsub.subscribe(channel)
            return self._pubsub
        except Exception as e:
            log.error(f"Redis subscribe error on {channel}: {e}")
            return None

    async def debug_keys(self):
        try:
            keys = await self.redis.keys("*")
            key_list = [k if isinstance(k, str) else k.decode() for k in keys[:20]]
            log.info(f"[REDIS KEYS] {len(keys)} total: {key_list}")
        except Exception as e:
            log.error(f"Redis debug_keys error: {e}")

class MemoryMock:
    """Mock Redis with Disk Persistence for local laptop setup."""
    def __init__(self, filename="local_state.json"): 
        self.filename = filename
        self.storage = self._load()
    
    def _load(self):
        if os.path.exists(self.filename):
            try:
                with open(self.filename, 'r') as f:
                    return json.load(f)
            except: return {}
        return {}

    def _save(self):
        try:
            with open(self.filename, 'w') as f:
                json.dump(self.storage, f)
        except Exception as e:
            log.error(f"Error saving local state: {e}")

    async def get(self, k): return self.storage.get(k)
    async def set(self, k, v, ex=None): 
        self.storage[k] = v
        self._save()
    async def exists(self, k): return k in self.storage
    async def keys(self, p):
        clean_p = p.replace('*', '')
        return [k for k in self.storage if k.startswith(clean_p)]
    async def delete(self, *keys): 
        for k in keys:
            if k in self.storage: del self.storage[k]
        self._save()
    async def lpush(self, k, v):
        if k not in self.storage: self.storage[k] = []
        self.storage[k].insert(0, v)
        self._save()
    async def lrange(self, k, s, e): return self.storage.get(k, [])[s:e+1]
    async def llen(self, k): return len(self.storage.get(k, []))
    async def ltrim(self, k, s, e): 
        self.storage[k] = self.storage.get(k, [])[s:e+1]
        self._save()
    async def ping(self): return True
    async def close(self): self._save()
    def pipeline(self): return self
    async def execute(self): return []
    async def publish(self, c, m): pass
    def pubsub(self): return self
    async def subscribe(self, c): pass
