import asyncio
import logging
import signal
import json
import uvicorn
from datetime import datetime
from contextlib import suppress

from config import SYMBOLS, CAPITAL
from core.state_manager import StateManager
from feeds.websocket_manager import WebSocketManager
from feeds.candle_feed import CandleFeedManager
from core.feature_engine import FeatureEngine
from api.app import create_app

from core.risk import RiskManager
from core.risk_guardian import RiskGuardian
from execution.order_engine import OrderEngine
from core.pnl_tracker import PnLTracker

from core.strategies.scalper import ScalperStrategy
from core.strategies.swing import SwingStrategy
from core.strategies.position import PositionStrategy

from core.telegram_notifier import TelegramNotifier
telegram = TelegramNotifier()

log = logging.getLogger("MAIN")

class RedisLogHandler(logging.Handler):
    def __init__(self, state: StateManager):
        super().__init__()
        self.state = state

    def emit(self, record):
        try:
            log_entry = {
                "time": datetime.now().strftime("%H:%M:%S"),
                "level": record.levelname,
                "name": record.name,
                "msg": self.format(record)
            }
            asyncio.create_task(self._push(log_entry))
        except Exception:
            pass

    async def _push(self, entry):
        if self.state.redis:
            await self.state.redis.lpush('logs:live', json.dumps(entry))
            await self.state.redis.ltrim('logs:live', 0, 199)

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
                log_equity(float(CAPITAL))
                log_balance([{"asset": "USDT", "balance": float(CAPITAL)}])
        except Exception as e:
            log.warning(f"Could not sync portfolio to dashboard: {e}")
        await asyncio.sleep(60)

async def daily_summary_loop(state: StateManager):
    """Nightly performance report for Telegram."""
    from datetime import timedelta
    while True:
        try:
            # Wait until midnight IST (18:30 UTC)
            now = datetime.utcnow()
            target = now.replace(hour=18, minute=30, second=0, microsecond=0)
            if now >= target:
                target += timedelta(days=1)
            
            wait_seconds = (target - now).total_seconds()
            log.info(f"📊 Daily summary scheduled in {wait_seconds/3600:.1f}h")
            await asyncio.sleep(wait_seconds)
            
            # Collect stats
            portfolio = await state.get_float('portfolio:value') or float(CAPITAL)
            daily_pnl = await state.get_float('pnl:24h') or 0.0
            scalper_pnl = await state.get_float('stats:scalper:pnl') or 0.0
            swing_pnl = await state.get_float('stats:swing:pnl') or 0.0
            position_pnl = await state.get_float('stats:position:pnl') or 0.0
            
            trades_raw = await state.redis.lrange('trade:history', 0, -1)
            trades = [json.loads(t) for t in trades_raw]
            today = datetime.utcnow().date()
            today_trades = [
                t for t in trades
                if datetime.fromisoformat(t['time']).date() == today
            ]
            wins = sum(1 for t in today_trades if t.get('pnl', 0) > 0)
            win_rate = (wins / len(today_trades) * 100) if today_trades else 0
            pnls = [t.get('pnl', 0) for t in today_trades]
            best = max(pnls) if pnls else 0
            worst = min(pnls) if pnls else 0
            
            await telegram.daily_summary(
                portfolio, daily_pnl, len(today_trades),
                win_rate, best, worst,
                scalper_pnl, swing_pnl, position_pnl
            )
            
            # Reset 24h PnL counter
            await state.redis.set('pnl:24h', 0)
        except Exception as e:
            log.error(f"Daily summary loop error: {e}")
            await asyncio.sleep(60)

async def main():
    # 1. Connect Redis first to setup logging
    state = StateManager()
    await state.connect()

    # 2. Setup Logging
    logging.basicConfig(level=logging.INFO, format='%(name)s: %(message)s')
    root_log = logging.getLogger()
    root_log.addHandler(RedisLogHandler(state))

    log.info("═" * 60)
    log.info("🚀 QUANT ENGINE v6.5 | Dashboard Overhaul Active")
    log.info("═" * 60)

    # 3. Initialize Settings if missing
    defaults = {
        "scalper_enabled": "true", "scalper_threshold": 0.45,
        "swing_enabled": "true", "swing_threshold": 0.55,
        "position_enabled": "true", "position_threshold": 0.65,
        "portfolio:value": float(CAPITAL)
    }
    for k, v in defaults.items():
        if await state.get(f"settings:{k}") is None:
            await state.set(f"settings:{k}", v)

    # 4. Init Managers
    ws_feed     = WebSocketManager(SYMBOLS, state)
    candle_feed = CandleFeedManager(SYMBOLS, ["1m", "5m", "15m", "1h", "4h", "1d"], state)
    features    = FeatureEngine(SYMBOLS, state)
    
    risk_manager  = RiskManager(state)
    risk_guardian = RiskGuardian(state)
    order_engine  = OrderEngine(state)
    pnl_tracker = PnLTracker(state)

    # 5. Init Parallel Strategies
    scalper  = ScalperStrategy(state, pnl_tracker, capital=200.0)
    swing    = SwingStrategy(state, pnl_tracker, capital=400.0)
    position = PositionStrategy(state, pnl_tracker, capital=400.0)

    # 6. Create Coroutines
    tasks = [
        asyncio.create_task(risk_manager.run_loop(interval=1)),
        asyncio.create_task(risk_guardian.run_loop(interval=60)),
        asyncio.create_task(order_engine.run_loop(interval=1)),
        asyncio.create_task(ws_feed.run_forever()),
        asyncio.create_task(candle_feed.run_forever()),
        asyncio.create_task(features.run_forever(interval_s=1)),
        asyncio.create_task(scalper.run_loop()),
        asyncio.create_task(swing.run_loop()),
        asyncio.create_task(position.run_loop()),
        asyncio.create_task(start_api_server(state)),
        asyncio.create_task(sync_dashboard(state)),
        asyncio.create_task(daily_summary_loop(state)),
    ]

    # Send startup notification
    portfolio = await state.get_float('portfolio:value') or float(CAPITAL)
    await telegram.bot_started(portfolio)

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
