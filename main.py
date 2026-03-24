import asyncio
import time
import logging
import signal
import json
import uvicorn
import os
from datetime import datetime
from contextlib import suppress

from config import SYMBOLS, CAPITAL, get_exchange
from core.state_manager import StateManager
from reporting.report_scheduler import ReportScheduler
from api.metrics import exporter as prometheus_exporter
from feeds.websocket_manager import WebSocketManager
from core.multi_asset_data_manager import MultiAssetDataManager
from core.portfolio_risk_manager import PortfolioRiskManager
from core.feature_engine import FeatureEngine
from api.app import create_app

from core.risk import RiskManager
from core.risk_guardian import RiskGuardian
from execution.order_engine import OrderEngine
from core.pnl_tracker import PnLTracker

from core.strategies.scalper import ScalperStrategy
from core.strategies.swing import SwingStrategy
from core.strategies.position import PositionStrategy
from core.strategies.ai_ensemble_strategy import AIEnsembleStrategy
from core.strategies.mean_reversion import MeanReversionStrategy
from core.strategies.ensemble_voting import EnsembleVotingStrategy
from ml.anomaly_detector import AnomalyDetector
from ml.boruta_selector import BorutaSelector
from ml.rf_gb_predictor import RFGBPredictor
from ml.parallel_predictor import ParallelMLPredictor
from ml.performance_monitor import PerformanceMonitor
from ml.signal_quality_tracker import SignalQualityTracker
from ml.auto_tuner import StrategyAutoTuner
from execution.pre_launch_validator import PreLaunchValidator
from execution.graduated_rollout import GraduatedRollout
from execution.alert_system import AlertSystem, monitor_critical_metrics

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
    port = int(os.environ.get("PORT", 8000))
    log.info(f"🌍 Starting API Server on port {port} (with proxy headers)")
    app = create_app(state)
    config = uvicorn.Config(app, host="0.0.0.0", port=port, log_level="warning", proxy_headers=True, forwarded_allow_ips='*')
    server = uvicorn.Server(config)
    await server.serve()

async def sync_dashboard(state: StateManager):
    """Sync live Binance portfolio to Firebase every 60s with retry logic."""
    from utils.firebase_client import log_equity, log_balance
    while True:
        try:
            acc = await state.get('binance:account')
            total_equity = float(CAPITAL)
            assets = [{"asset": "USDT", "balance": total_equity}]
            
            if acc:
                total_equity = float(acc.get('totalWalletBalance', 0)) + float(acc.get('totalUnrealizedProfit', 0))
                found_assets = []
                for a in acc.get('assets', []):
                    bal = float(a.get('walletBalance', 0))
                    if bal > 0:
                        found_assets.append({"asset": a['asset'], "balance": bal})
                if found_assets:
                    assets = found_assets

            # Protective wrappers for Firebase calls
            try: log_equity(total_equity)
            except Exception as fe: log.error(f"Firebase Equity Log Error: {fe}")
            
            try: log_balance(assets)
            except Exception as fb: log.error(f"Firebase Balance Log Error: {fb}")
            
        except Exception as e:
            log.warning(f"Could not sync portfolio to dashboard: {e}")
            await asyncio.sleep(10) # Back off a bit on error
            continue
            
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
            
            # Wrap Telegram call in try-except to prevent bot crash
            try:
                await telegram.daily_summary(
                    portfolio, daily_pnl, len(today_trades),
                    win_rate, best, worst,
                    scalper_pnl, swing_pnl, position_pnl
                )
            except Exception as te:
                log.error(f"Telegram Daily Summary Error: {te}")
            
            # Reset 24h PnL counter
            await state.redis.set('pnl:24h', 0)
        except Exception as e:
            log.error(f"Daily summary loop error: {e}")
            await asyncio.sleep(60)

async def ml_engine_loop(state: StateManager, ml_predictor: ParallelMLPredictor, perf_monitor: PerformanceMonitor, signal_tracker: SignalQualityTracker):
    """
    Main ML engine loop - updates ensemble predictions in Redis every 60s.
    Also tracks performance latency and signal quality.
    """
    log.info("🧠 ML Engine Loop Started (with Monitoring)")
    from config import SYMBOLS
    while True:
        try:
            start_total = time.time()
            for symbol in SYMBOLS:
                # Get latest 1h candle data for features
                df = await state.get_df(f"ohlcv:1h:{symbol}", n=100)
                if df is None or df.empty:
                    continue
                
                price = float(df['close'].iloc[-1])
                features = {
                    'open': float(df['open'].iloc[-1]),
                    'high': float(df['high'].iloc[-1]),
                    'low': float(df['low'].iloc[-1]),
                    'close': price,
                    'volume': float(df['volume'].iloc[-1]),
                }
                
                # Run parallel prediction and track latency
                start_pred = time.time()
                prediction = await ml_predictor.predict_all(features, symbol)
                latency_ms = (time.time() - start_pred) * 1000
                perf_monitor.record_latency('ensemble', latency_ms)

                # Store in Redis for strategies to consume
                await state.set(f"ml_signal:{symbol}", prediction)
                
                # Record for quality tracking (1h, 4h, 1d evaluation)
                await signal_tracker.record_signal(
                    symbol, 
                    prediction['signal'], 
                    prediction['confidence'], 
                    price, 
                    time.time()
                )
                
                log.info(f"🧠 [{symbol}] Ensemble: {prediction['signal']} (Conf: {prediction['confidence']:.2%}) | Latency: {latency_ms:.1f}ms")
            
            # Record total loop latency
            perf_monitor.record_latency('total_loop', (time.time() - start_total) * 1000)
                
        except Exception as e:
            log.error(f"ML Engine Error: {e}")
        await asyncio.sleep(60)

async def main():
    # 3. Connect to State Manager (Redis)
    redis_url = os.getenv("REDIS_URL", "redis://localhost:6379")
    masked_url = redis_url.split('@')[-1] if '@' in redis_url else redis_url
    log.info(f"💾 Connecting to Redis at: {masked_url}")
    
    state = StateManager()
    await state.connect()
    
    # Verify Telegram Connection
    await telegram.verify_connection()

    # --- PHASE 7: PRE-LAUNCH VALIDATION ---
    is_live = os.getenv('ENABLE_LIVE_TRADING', 'false').lower() == 'true'
    if is_live:
        log.warning("🚨 LIVE TRADING MODE ENABLED")
        validator = PreLaunchValidator(state)
        if not await validator.run_full_validation():
            log.error("❌ PRE-LAUNCH VALIDATION FAILED - CRITICAL ERRORS DETECTED")
            validator.print_validation_report()
            log.error("Check your Railway Environment Variables (API Keys, Redis URL, Model Files).")
            # Wait a bit to ensure logs are sent to Railway
            await asyncio.sleep(2)
            return
        validator.print_validation_report()
        log.info("✅ ALL PRE-LAUNCH CHECKS PASSED - STARTING LIVE TRADING")
    else:
        log.info("🧪 Running in PAPER TRADING mode")

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

    # 4. Initialize Data Sources & Shared State
    ws_feed     = WebSocketManager(SYMBOLS, state)
    # CandleFeedManager replaced by MultiAssetDataManager in Phase 8
    features    = FeatureEngine(SYMBOLS, state)
    risk_manager  = RiskManager(state)
    portfolio_risk = PortfolioRiskManager(risk_manager)
    risk_guardian = RiskGuardian(state)
    order_engine  = OrderEngine(state, portfolio_risk=portfolio_risk)
    
    # 4.1 Initialize Multi-Asset Data Manager
    exchange = get_exchange(use_testnet=True)
    data_manager = MultiAssetDataManager(exchange, state)
    
    pnl_tracker = PnLTracker(state)
    ml_predictor = ParallelMLPredictor(state)
    perf_monitor = PerformanceMonitor()
    signal_tracker = SignalQualityTracker(state)
    
    # --- PHASE 7: EXECUTION TOOLS ---
    alert_system = AlertSystem(state)
    rollout = GraduatedRollout(state, start_capital=float(CAPITAL))
    auto_tuner = StrategyAutoTuner(state)

    # --- PHASE 9: MONITORING & REPORTING ---
    report_scheduler = ReportScheduler(state)
    report_scheduler.start()

    # --- START API IMMEDIATELY FOR HEALTH CHECKS ---
    api_task = asyncio.create_task(start_api_server(state))
    # Give API a moment to bind
    await asyncio.sleep(1)

    # 5. Init Parallel Strategies (Using Graduated Rollout)
    initial_cap = await rollout.get_position_size()
    strat_cap = initial_cap / 6
    log.info(f"💰 Initial Capital Allocation (Phase: {rollout.current_phase}): ${initial_cap:.2f} total (${strat_cap:.2f}/strategy)")
    
    scalper  = ScalperStrategy(state, pnl_tracker, capital=strat_cap)
    swing    = SwingStrategy(state, pnl_tracker, capital=strat_cap)
    position = PositionStrategy(state, pnl_tracker, capital=strat_cap)
    ai_ensemble = AIEnsembleStrategy(state, pnl_tracker, capital=strat_cap)
    mean_revert = MeanReversionStrategy(state, pnl_tracker, capital=strat_cap)
    ensemble_vote = EnsembleVotingStrategy(state, pnl_tracker, capital=strat_cap)

    # 5.1 Startup Checks (Paper 1 & 4) - Wrapped in task to prevent blocking
    async def run_startup_checks():
        log.info("🔍 Running startup Anomaly Detection...")
        detector = AnomalyDetector()
        for symbol in SYMBOLS:
            df_1h = await state.get_df(f"ohlcv:1h:{symbol}", n=100)
            if df_1h is not None:
                res = detector.detect(df_1h['close'].tolist())
                log.info(f"Anomaly Check [{symbol}]: Z={res['z_score']:.2f} {'(!!!)' if res['is_abnormal'] else '(Normal)'}")
    
    asyncio.create_task(run_startup_checks())

    # 5.2 Background ML Tasks
    async def train_ml_models():
        log.info("🔄 Background ML training started...")
        rf_gb = RFGBPredictor()
        boruta = BorutaSelector()
        for symbol in SYMBOLS:
            df_full = await state.get_df(f"ohlcv:1h:{symbol}", n=1000)
            if df_full is not None:
                await asyncio.get_event_loop().run_in_executor(None, rf_gb.train, df_full)
                target = df_full['close'].shift(-1) > df_full['close']
                await asyncio.get_event_loop().run_in_executor(None, boruta.select_features, df_full, target)
        log.info("✅ Background ML training complete.")

    asyncio.create_task(train_ml_models())

    # 6. Create Coroutines
    tasks = [
        api_task,
        asyncio.create_task(sync_dashboard(state), name="DASH_SYNC"),
        asyncio.create_task(risk_manager.run_loop(interval=1), name="RISK_MGR"),
        asyncio.create_task(risk_guardian.run_loop(interval=60), name="RISK_GTD"),
        asyncio.create_task(order_engine.run_loop(interval=1), name="ORDER_ENG"),
        asyncio.create_task(ws_feed.run_forever(), name="WS_FEED"),
        asyncio.create_task(data_manager.run_loop(interval_seconds=60), name="DATA_MGR"),
        asyncio.create_task(features.run_forever(interval_s=1), name="FEAT_ENG"),
        
        # Strategy Tasks
        asyncio.create_task(scalper.run_loop(), name="SCALPER"),
        asyncio.create_task(swing.run_loop(), name="SWING"),
        asyncio.create_task(position.run_loop(), name="POSITION"),
        asyncio.create_task(ai_ensemble.run_loop(), name="AI_ENSEMBLE"),
        asyncio.create_task(mean_revert.run(), name="MEAN_REVERT"),
        asyncio.create_task(ensemble_vote.run(), name="ENSEMBLE_VOTE"),
        asyncio.create_task(ml_engine_loop(state, ml_predictor, perf_monitor, signal_tracker), name="ML_ENGINE"),
        asyncio.create_task(perf_monitor.log_stats_periodically(300), name="PERF_STATS"),
        
        asyncio.create_task(daily_summary_loop(state), name="DAILY_SUM"),
        
        # Phase 7 Monitoring & Tuning
        asyncio.create_task(monitor_critical_metrics(state, alert_system), name="ALERT_MONITOR"),
        asyncio.create_task(auto_tuner.run_periodic_tuning(SYMBOLS), name="AUTO_TUNER"),
        
        # Phase 9 Prometheus Update
        asyncio.create_task(prometheus_exporter.update_loop(state), name="PROMETHEUS_METRICS")
    ]

    # Send startup notification
    portfolio = await state.get_float('portfolio:value') or float(CAPITAL)
    await telegram.bot_started(portfolio)

    # Graceful shutdown handler
    loop = asyncio.get_event_loop()
    components = [ws_feed, data_manager, features, risk_guardian, order_engine, scalper, swing, position]
    for sig in (signal.SIGINT, signal.SIGTERM):
        with suppress(NotImplementedError):
            loop.add_signal_handler(sig, lambda: asyncio.create_task(shutdown(tasks, *components)))

    log.info("✅ All systems initialized. Gathering tasks...")
    
    # Task Watchdog: Ensure critical tasks are monitored
    while True:
        try:
            # Re-gather tasks periodically or wait for completion with exception handling
            done, pending = await asyncio.wait(
                tasks, 
                return_when=asyncio.FIRST_EXCEPTION
            )
            
            for task in done:
                if task.exception():
                    log.critical(f"🚨 CRITICAL TASK FAILED: {task.get_name() or task} | Exception: {task.exception()}")
                    # Optionally restart or handle specific failures
            
            if not pending: break # All tasks finished? (Unexpected in a bot)
            await asyncio.sleep(5)
            
        except asyncio.CancelledError:
            break
        except Exception as e:
            log.error(f"Task monitoring error: {e}")
            await asyncio.sleep(5)

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
