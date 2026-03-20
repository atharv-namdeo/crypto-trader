"""
main.py — Quant Engine v5.0 (Phase 2: Async + Redis Architecture)

Starts up:
1. StateManager (Redis Interface)
2. WebSocketFeed (Binance WS streams)
3. CandleFeed (OHLCV multi-timeframe aggregation)
4. FeatureEngine (60+ features computed every 1s)
5. FastAPI Dashboard API
6. Strategy & Position Loop (Ensemble scoring every 1s based on latest Redis features)
"""

import asyncio
import logging
import signal
import uvicorn
from contextlib import suppress

from config import SYMBOLS, CAPITAL
from core.state_manager import StateManager
from feeds.websocket_manager import WebSocketManager
from feeds.candle_feed import CandleFeedManager
from core.feature_engine import FeatureEngine
from api.app import create_app

# The existing pure-logic rules and management (Phase 1 logic imported)
from core.regime import RegimeClassifier
from core.ensemble import compute_ensemble
from core.position_manager import PositionManager
from core.risk import RiskManager
from execution.order_engine import OrderEngine

# Import Strategies
from strategies.mtf import MomentumTrendFollowing
from strategies.stat_arb import StatArb
from strategies.mean_reversion import MeanReversion
from strategies.breakout import VolatilityBreakout
from strategies.obis import OrderBookImbalance
from strategies.vwap_reversion import VWAPReversion
from strategies.liquidity_sweep import LiquiditySweep
from strategies.mtf_macd import MTFMACD
from strategies.rsi_divergence import RSIDivergence
from strategies.fibonacci import FibonacciRetracement
from strategies.ichimoku import IchimokuCloud
from strategies.atr_expansion import ATRExpansion
from strategies.volume_profile import VolumeProfile
from strategies.pivot_points import PivotPoints
from strategies.psar import ParabolicSAR
from strategies.supertrend import SupertrendStrategy
from strategies.gann import GANNFan
from strategies.harmonic import HarmonicPatterns
from strategies.liquidity_grabs import LiquidityGrabs
from strategies.trend_exhaustion import TrendExhaustion

# ML Models
from ml.xgboost_model import XGBoostStrategy
from ml.lstm_model import LSTMStrategy

log = logging.getLogger("MAIN")

ALL_STRATEGIES = {
    'MTF':             MomentumTrendFollowing(),
    'STAT_ARB':        StatArb(),
    'MEAN_REVERSION':  MeanReversion(),
    'BREAKOUT':        VolatilityBreakout(),
    'OBIS':            OrderBookImbalance(),
    'VWAP_REVERSION':  VWAPReversion(),
    'LIQUIDITY_SWEEP': LiquiditySweep(),
    'MTF_MACD':        MTFMACD(),
    'RSI_DIV':         RSIDivergence(),
    'FIBONACCI':       FibonacciRetracement(),
    'ICHIMOKU':        IchimokuCloud(),
    'ATR_EXPANSION':   ATRExpansion(),
    'VOLUME_PROFILE':  VolumeProfile(),
    'PIVOT_POINTS':    PivotPoints(),
    'PSAR':            ParabolicSAR(),
    'SUPERTREND':      SupertrendStrategy(),
    'GANN_FAN':        GANNFan(),
    'HARMONIC':        HarmonicPatterns(),
    'LIQUIDITY_GRAB':  LiquidityGrabs(),
    'TREND_EXHAUST':   TrendExhaustion(),
    'XGBOOST':         XGBoostStrategy(),
    'LSTM':            LSTMStrategy(),
}


class TradingEngine:
    def __init__(self, state: StateManager):
        self.state = state
        self.running = False
        self.regime = RegimeClassifier()
        
    async def run_forever(self, interval_s: int = 1):
        """Main strategy loop: reads from Redis, computes signals, updates ensemble score."""
        self.running = True
        log.info("🧠 Brain Engine Loop Started")
        
        while self.running:
            try:
                for symbol in SYMBOLS:
                    await self._process_symbol(symbol)
                    
            except asyncio.CancelledError:
                break
            except Exception as e:
                log.error(f"BrainEngine loop error: {e}")
                
            await asyncio.sleep(interval_s)

    async def _process_symbol(self, symbol: str):
        price = await self.state.get_float(f"price:{symbol}")
        f     = await self.state.get(f"features:{symbol}")
        df_1h = await self.state.get_df(f"ohlcv:1h:{symbol}", n=200)
        
        if not price or not f or df_1h is None or len(df_1h) < 20:
            return

        regime_data = self.regime.classify(df_1h)
        regime_label = regime_data['regime']
        regime_conf  = regime_data['confidence']
        await self.state.set(f"regime:{symbol}", regime_data)

        signal_map = {}
        for name, strategy in ALL_STRATEGIES.items():
            try:
                if hasattr(strategy, 'calculate_signal_from_features'):
                    sig = strategy.calculate_signal_from_features(f)
                else:
                    sig = strategy.calculate_signal(df_1h, macro_trend="BULLISH", portfolio_value=CAPITAL)
                
                if sig:
                    if 'confidence' not in sig:
                        sig['confidence'] = 0.5
                    signal_map[name] = sig
            except Exception:
                pass

        ensemble = compute_ensemble(signal_map, regime_label, regime_conf)
        await self.state.set(f"ensemble:{symbol}", ensemble)

# ── ORCHESTRATOR ──────────────────────────────────────────────────────────

async def start_api_server(state: StateManager):
    app = create_app(state)
    config = uvicorn.Config(app, host="0.0.0.0", port=8000, log_level="warning")
    server = uvicorn.Server(config)
    await server.serve()

async def main():
    logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(name)s] %(levelname)s: %(message)s')
    log.info("═" * 60)
    log.info("🚀 QUANT ENGINE v6.0 | Live Execution Async + Redis")
    log.info("═" * 60)

    # 1. Connect Redis
    state = StateManager()
    await state.connect()

    # 2. Init Managers
    ws_feed     = WebSocketManager(SYMBOLS, state)
    candle_feed = CandleFeedManager(SYMBOLS, ["1m", "5m", "15m", "1h", "4h"], state)
    features    = FeatureEngine(SYMBOLS, state)
    engine      = TradingEngine(state)
    
    risk_guardian = RiskManager(state)
    position_manager = PositionManager(state)
    order_engine = OrderEngine(state)

    # 3. Create Coroutines
    tasks = [
        asyncio.create_task(risk_guardian.run_loop(interval=1)),
        asyncio.create_task(position_manager.run_loop(interval=5)),
        asyncio.create_task(order_engine.run_loop(interval=1)),
        asyncio.create_task(ws_feed.run_forever()),
        asyncio.create_task(candle_feed.run_forever()),
        asyncio.create_task(features.run_forever(interval_s=1)),
        asyncio.create_task(engine.run_forever(interval_s=1)),
        asyncio.create_task(start_api_server(state)),
    ]

    # Graceful shutdown handler
    loop = asyncio.get_event_loop()
    components = [ws_feed, candle_feed, features, engine, risk_guardian, position_manager, order_engine]
    for sig in (signal.SIGINT, signal.SIGTERM):
        with suppress(NotImplementedError):
            loop.add_signal_handler(sig, lambda: asyncio.create_task(shutdown(tasks, *components)))

    log.info("✅ All systems initialized. Gathering tasks...")
    await asyncio.gather(*tasks)

async def shutdown(tasks, *components):
    log.warning("🛑 SHUTTING DOWN ENGINE...")
    for c in components:
        if hasattr(c, 'stop'):
            c.stop()
    for t in tasks:
        t.cancel()
    await asyncio.sleep(1)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
