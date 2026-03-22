"""
main.py — Quant Engine v6.0 (Phase 3: Multi-Strategy Parallel Architecture)

Starts up:
1. StateManager (Redis Interface)
2. WebSocketFeed (Binance WS streams)
3. CandleFeed (OHLCV multi-timeframe aggregation)
4. FeatureEngine (60+ features computed every 1s)
5. FastAPI Dashboard API
6. PnLTracker & 3 Independent Strategies (Scalper, Swing, Position)
7. OrderEngine (Execution)
8. RiskGuardian (Safety limits)
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

from core.risk import RiskManager
from execution.order_engine import OrderEngine
from core.pnl_tracker import PnLTracker

from core.strategies.scalper import ScalperStrategy
from core.strategies.swing import SwingStrategy
from core.strategies.position import PositionStrategy

log = logging.getLogger("MAIN")

async def start_api_server(state: StateManager):
    """Run FastAPI dashboard backend."""
    app = create_app(state)
    config = uvicorn.Config(app, host="0.0.0.0", port=8000, log_level="warning")
    server = uvicorn.Server(config)
    await server.serve()

async def sync_dashboard(state: StateManager):
    """Sync live Binance portfolio to Firebase every 60s."""
    from utils.firebase_client import log_equity, log_balance
    while True:
        try:
            acc = await state.get('binance:account')
            if acc:
                total_equity = float(acc.get('totalWalletBalance', 0)) + float(acc.get('totalUnrealizedProfit', 0))
                assets = []
                for a in acc.get('assets', []):
                    bal = float(a.get('walletBalance', 0))
                    if bal > 0:
                        assets.append({"asset": a['asset'], "balance": bal})
                if not assets:
                    assets = [{"asset": "USDT", "balance": total_equity}]
                log_equity(total_equity)
                log_balance(assets)
            else:
                from config import CAPITAL
                log_equity(float(CAPITAL))
                log_balance([{"asset": "USDT", "balance": float(CAPITAL)}])
        except Exception as e:
            log.warning(f"Could not sync portfolio to dashboard: {e}")
        await asyncio.sleep(60)

async def main():
    logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(name)s] %(levelname)s: %(message)s')
    log.info("═" * 60)
    log.info("🚀 QUANT ENGINE v6.0 | Live Execution Async + Redis")
    log.info("═" * 60)

    # 1. Connect Redis
    state = StateManager()
    await state.connect()
    
    # Initialize portfolio value
    existing = await state.get_float('portfolio:value')
    if not existing:
        await state.set('portfolio:value', float(CAPITAL))

    # 2. Init Managers
    ws_feed     = WebSocketManager(SYMBOLS, state)
    candle_feed = CandleFeedManager(SYMBOLS, ["1m", "5m", "15m", "1h", "4h", "1d"], state)
    features    = FeatureEngine(SYMBOLS, state)
    
    risk_guardian = RiskManager(state)
    order_engine = OrderEngine(state)
    pnl_tracker = PnLTracker(state)

    # 3. Init Parallel Strategies
    scalper  = ScalperStrategy(state, pnl_tracker, capital=200.0)
    swing    = SwingStrategy(state, pnl_tracker, capital=400.0)
    position = PositionStrategy(state, pnl_tracker, capital=400.0)

    # 4. Create Coroutines
    tasks = [
        asyncio.create_task(risk_guardian.run_loop(interval=1)),
        asyncio.create_task(order_engine.run_loop(interval=1)),
        asyncio.create_task(ws_feed.run_forever()),
        asyncio.create_task(candle_feed.run_forever()),
        asyncio.create_task(features.run_forever(interval_s=1)),
        asyncio.create_task(scalper.run_loop()),
        asyncio.create_task(swing.run_loop()),
        asyncio.create_task(position.run_loop()),
        asyncio.create_task(start_api_server(state)),
        asyncio.create_task(sync_dashboard(state)),
    ]

    # Graceful shutdown handler
    loop = asyncio.get_event_loop()
    components = [ws_feed, candle_feed, features, risk_guardian, order_engine, scalper, swing, position]
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
        if hasattr(c, 'running'):
            c.running = False
    for t in tasks:
        t.cancel()
    await asyncio.sleep(1)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
