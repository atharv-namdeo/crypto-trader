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
from core.position_tracker import PositionTracker
from core.risk import RiskManager

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
}


class TradingEngine:
    def __init__(self, state: StateManager):
        self.state = state
        self.running = False
        
        self.regime     = RegimeClassifier()
        self.positions  = PositionTracker()
        self.risk       = RiskManager()
        
    async def run_forever(self, interval_s: int = 1):
        """Main strategy loop: reads from Redis, computes signals, manages positions."""
        self.running = True
        log.info("🚀 Trading Engine Loop Started")
        
        start_capital = CAPITAL
        current_capital = CAPITAL
        
        cycle = 0
        while self.running:
            cycle += 1
            try:
                # 1. Check daily drawdown
                if self.risk.check_daily_drawdown(start_capital, current_capital):
                    log.critical("🛑 HALTING ENGINE — daily drawdown hit")
                    break

                for symbol in SYMBOLS:
                    await self._process_symbol(symbol, current_capital)

                # Sync state positions to Redis for the API/Dashboard to read
                for sym, pos in self.positions.get_all_positions().items():
                    if pos:
                        # Convert dataclass to dict
                        await self.state.set_position(sym, pos.__dict__)

                # Store risk state
                total_heat = self.positions.total_heat(current_capital, current_capital)
                await self.state.set("risk_state", {"total_heat": total_heat})

            except asyncio.CancelledError:
                break
            except Exception as e:
                log.error(f"Trading loop error: {e}")
                
            await asyncio.sleep(interval_s)

    async def _process_symbol(self, symbol: str, capital: float):
        # Read pre-computed data from Redis
        price = await self.state.get_float(f"price:{symbol}")
        f     = await self.state.get(f"features:{symbol}")
        df_1h = await self.state.get_df(f"ohlcv:1h:{symbol}", n=200)
        
        if not price or not f or df_1h is None or len(df_1h) < 20:
            return

        # 1. Regime Detection (We compute it from the up-to-date 1h df)
        regime_data = self.regime.classify(df_1h)
        regime_label = regime_data['regime']
        regime_conf  = regime_data['confidence']
        
        await self.state.set(f"regime:{symbol}", regime_data)

        # 2. Compute Algos (Phase 2 optimization: ideally algorithms read from 'f' dict
        #    instead of pandas DF, but to keep Phase 1 algorithms working without rewrite,
        #    we pass the pandas DF as before).
        signal_map = {}
        for name, strategy in ALL_STRATEGIES.items():
            try:
                # Note: full implementation would adapt strategies to use `f` dict directly
                sig = strategy.calculate_signal(df_1h, macro_trend="BULLISH", portfolio_value=capital)
                if sig:
                    if 'confidence' not in sig:
                        sig['confidence'] = 0.5
                    signal_map[name] = sig
            except Exception:
                pass

        # 3. Ensemble Scorer
        ensemble = compute_ensemble(signal_map, regime_label, regime_conf)
        score      = ensemble['final_score']
        action     = ensemble['action']
        conviction = ensemble['conviction']
        
        await self.state.set(f"ensemble:{symbol}", ensemble)

        # 4. Position Management
        atr = f.get('atr_14_1h', price * 0.01)
        pos_action = self.positions.update(symbol, price, atr, score)
        
        if pos_action['action'] == 'FLIP':
            log.info(f"🔄 {symbol} POSITION FLIP → {pos_action['new_side']}")
            self._open(symbol, score, conviction, price, atr, capital, force_side=pos_action['new_side'])
            return
            
        if not self.positions.has_position(symbol) and action in ('LONG', 'SHORT'):
            self._open(symbol, score, conviction, price, atr, capital)

    def _open(self, symbol, score, conviction, price, atr, capital, force_side=None):
        side = force_side if force_side else ('LONG' if score > 0 else 'SHORT')
        sizing = self.risk.compute_position_size(capital, conviction, atr, price)
        qty = sizing['qty']
        
        if qty <= 0:
            return
            
        stop_dist = 1.5 * atr
        stop = price - stop_dist if side == 'LONG' else price + stop_dist
        tp1  = price + stop_dist * 2.0 if side == 'LONG' else price - stop_dist * 2.0
        
        current_heat = self.positions.total_heat(capital, capital)
        if not self.risk.validate_trade(side, price, stop, tp1, qty, capital, current_heat):
            return
            
        self.positions.open_position(symbol, side, price, qty, atr, score)
        log.info(f"✅ {symbol} {side} OPENED @ {price:.4f} | score={score:+.2f}")


# ── ORCHESTRATOR ──────────────────────────────────────────────────────────

async def start_api_server(state: StateManager):
    app = create_app(state)
    config = uvicorn.Config(app, host="0.0.0.0", port=8000, log_level="warning")
    server = uvicorn.Server(config)
    await server.serve()

async def main():
    logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(name)s] %(levelname)s: %(message)s')
    log.info("═" * 60)
    log.info("🚀 QUANT ENGINE v5.0 | Async + Redis")
    log.info("═" * 60)

    # 1. Connect Redis
    state = StateManager()
    await state.connect()

    # 2. Init Managers
    ws_feed     = WebSocketManager(SYMBOLS, state)
    candle_feed = CandleFeedManager(SYMBOLS, ["1m", "5m", "15m", "1h", "4h"], state)
    features    = FeatureEngine(SYMBOLS, state)
    engine      = TradingEngine(state)

    # 3. Create Coroutines
    tasks = [
        asyncio.create_task(ws_feed.run_forever()),
        asyncio.create_task(candle_feed.run_forever()),
        asyncio.create_task(features.run_forever(interval_s=1)),
        asyncio.create_task(engine.run_forever(interval_s=1)),
        asyncio.create_task(start_api_server(state)),
    ]

    # Graceful shutdown handler
    loop = asyncio.get_event_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        with suppress(NotImplementedError):  # Windows doesn't support some signals
            loop.add_signal_handler(sig, lambda: asyncio.create_task(shutdown(tasks, ws_feed, candle_feed, features, engine)))

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
