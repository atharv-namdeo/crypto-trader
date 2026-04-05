"""
core/regime_detector.py
Expert-Grade Market State Identification - Phase 6
"""

import logging
import asyncio
import numpy as np
import pandas as pd
from core.state_manager import StateManager
from core.utils import compute_adx, compute_atr, compute_rsi

log = logging.getLogger("RegimeDetector")

class RegimeDetector:
    def __init__(self, state: StateManager):
        self.state = state
        self.running = False

    async def run_loop(self):
        self.running = True
        log.info("🚀 Market Regime Detector started")
        
        while self.running:
            try:
                # 1. Global Regime (BTC)
                await self._detect_regime("BTC/USDT", is_global=True)
                
                # 2. Local Regimes for all traded symbols
                from config import SYMBOLS
                for symbol in SYMBOLS:
                    await self._detect_regime(symbol)
                    
                await asyncio.sleep(300) # Every 5 minutes
            except Exception as e:
                log.error(f"Regime detection error: {e}")
                await asyncio.sleep(60)

    async def _detect_regime(self, symbol: str, is_global: bool = False):
        try:
            from core.strategies.regime_classifier import AdvancedRegimeDetector
            detector = AdvancedRegimeDetector()
            
            # Fetch 1h OHLCV
            df = await self.state.get_ohlcv(symbol, "1h", limit=100)
            if df.empty or len(df) < 50: return
            
            # Advanced Classification
            phase = detector.classify_market(df)
            regime = phase.value
            
            # Additional metrics for Dashboard
            from core.utils import compute_adx, compute_atr, compute_rsi
            adx = compute_adx(df, window=14)
            atr = compute_atr(df, window=14)
            rsi = compute_rsi(df['close'], window=14)
            
            curr_adx = adx.iloc[-1]
            curr_atr_pct = (atr.iloc[-1] / df['close'].iloc[-1]) * 100
            curr_rsi = rsi.iloc[-1]
            
            # Store in Redis
            key = "market:regime:global" if is_global else f"market:regime:{symbol}"
            data = {
                'regime': regime,
                'adx': float(curr_adx),
                'atr_pct': float(curr_atr_pct),
                'rsi': float(curr_rsi),
                'timestamp': pd.Timestamp.now().timestamp()
            }
            await self.state.set(key, data)
            
            if is_global:
                log.info(f"🌍 Global Regime (10-Phase): {regime}")
                
        except Exception as e:
            log.debug(f"Could not compute regime for {symbol}: {e}")

    def stop(self):
        self.running = False
