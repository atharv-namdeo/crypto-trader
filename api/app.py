import mimetypes
mimetypes.init()
mimetypes.add_type('application/javascript', '.js')
mimetypes.add_type('text/css', '.css')

import json
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Body, Depends
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from starlette.responses import FileResponse, StreamingResponse
import asyncio
import logging
import time
import io
import csv
from datetime import datetime
from core.state_manager import StateManager
from api.metrics import router as metrics_router

from security.production_hardening import setup_production_security, verify_api_key

log = logging.getLogger("FastAPI")

def create_app(state: StateManager):
    app = FastAPI(title="Quant Engine API", version="5.0")
    
    # --- PHASE 10: PRODUCTION SECURITY ---
    setup_production_security(app)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=[
            "https://crypto-trader-beta.vercel.app",
            "http://localhost:5173",
            "http://127.0.0.1:5173",
            "*"
        ],
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(metrics_router)

    @app.get("/health")
    async def health():
        return {"status": "ok", "redis": bool(state.redis)}

    @app.get("/api/v1/health")
    async def get_health():
        return {"status": "ok", "redis": state.redis is not None}

    @app.post("/api/v1/order", dependencies=[Depends(verify_api_key)])
    async def manage_order(payload: dict = Body(...)):
        """Close now or move stop"""
        symbol = payload.get('symbol')
        action = payload.get('action') # CLOSE_NOW or MOVE_STOP
        if symbol:
            await state.set(f"order_request:{symbol}", payload)
            return {"status": "request_sent", "payload": payload}
        return {"status": "error", "message": "Symbol required"}

    @app.get("/api/v1/settings")
    async def get_settings():
        settings_keys = [
            "scalper_enabled", "scalper_threshold", 
            "swing_enabled", "swing_threshold", 
            "position_enabled", "position_threshold"
        ]
        settings = {}
        for key in settings_keys:
            settings[key] = await state.get(f"settings:{key}")
        return {"data": settings}

    @app.get("/api/v1/trades")
    async def get_trades(limit: int = 50, offset: int = 0, symbol: str = None):
        """Paginated trade history from Redis/Firebase."""
        trades_raw = await state.redis.lrange('trade:history', offset, offset + limit - 1)
        trades = [json.loads(t) for t in trades_raw]
        if symbol:
            trades = [t for t in trades if t.get('symbol') == symbol]
        return {"data": trades, "count": len(trades)}

    @app.get("/api/v1/export/trades")
    async def export_trades():
        """Export all trades from local JSON DB as CSV"""
        from core.firebase_manager import FirebaseManager
        fm = FirebaseManager()
        trades_dict = fm.get("trades") or {}
        trades = list(trades_dict.values()) if isinstance(trades_dict, dict) else []
        
        if not trades:
            return {"status": "error", "message": "No trades found in local database"}

        output = io.StringIO()
        writer = csv.DictWriter(output, fieldnames=trades[0].keys() if trades else [])
        writer.writeheader()
        writer.writerows(trades)
        
        output.seek(0)
        return StreamingResponse(
            iter([output.getvalue()]),
            media_type="text/csv",
            headers={"Content-Disposition": f"attachment; filename=trades_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"}
        )

    @app.post("/api/v1/settings", dependencies=[Depends(verify_api_key)])
    async def update_settings(settings: dict = Body(...)):
        for k, v in settings.items():
            await state.set(f"settings:{k}", v)
        return {"status": "updated"}

    @app.get("/ml/ensemble-signal/{symbol}")
    async def get_ensemble_signal(symbol: str):
        data = await state.get(f"ensemble_signal:{symbol}")
        return json.loads(data) if data else {"status": "no_data"}

    @app.get("/ml/anomaly/{symbol}")
    async def get_anomaly(symbol: str):
        data = await state.get(f"anomaly:{symbol}")
        return json.loads(data) if data else {"status": "no_data"}

    @app.get("/ml/boruta-features/{symbol}")
    async def get_boruta_features(symbol: str):
        data = await state.get(f"boruta_features:{symbol}")
        return {"features": data} if data else {"status": "no_data"}

    @app.get("/strategies")
    async def get_strategy_status():
        if not state.redis: return {"error": "Redis not connected"}
        stats = {}
        for s in ["scalper", "swing", "position", "ai_ensemble"]:
            stats[s] = {
                "trades": int(await state.get(f"stats:{s}:trades") or 0),
                "wins": int(await state.get(f"stats:{s}:wins") or 0),
                "pnl": float(await state.get(f"stats:{s}:pnl") or 0.0),
                "pos_count": len(await state.redis.keys(f"{s}:pos:*") if state.redis else [])
            }
        return stats

    @app.get("/candles")
    async def get_candles(symbol: str, interval: str, limit: int = 200):
        # Read from Redis: ohlcv:{interval}:{symbol}
        df = await state.get_df(f"ohlcv:{interval}:{symbol}")
        if df is None:
            return []
        
        # Ensure we return the requested limit
        candles = df.tail(limit)
        return [
            {
                'time': int(row['timestamp'].timestamp()) if hasattr(row['timestamp'], 'timestamp') else int(row['timestamp'] / 1000),
                'open':   float(row['open']),
                'high':   float(row['high']),
                'low':    float(row['low']),
                'close':  float(row['close']),
                'volume': float(row['volume'])
            }
            for _, row in candles.iterrows()
        ]

    @app.websocket("/ws")
    async def websocket_endpoint(websocket: WebSocket):
        await websocket.accept()
        log.info(f"✅ Dashboard WS connected")
        
        from config import SYMBOLS, STRATEGY_ALLOCATIONS
        
        try:
            while True:
                if not state.redis:
                    await websocket.send_json({"type": "info", "data": "Waiting for Redis..."})
                    await asyncio.sleep(5)
                    continue

                payload = {
                    "type": "engine_update", 
                    "data": {
                        "market": {},
                        "exchange": "Binance Demo",
                        "node": "Binance-Executor-01",
                        "sector_heat": {},
                        "signal_heatmap": [],
                        "strategies": {},
                        "portfolio": {},
                        "status": "ACTIVE",
                        "regime": "NEUTRAL",
                        "positions": [],
                        "orders": [],
                        "signals": [],
                        "trades": [],
                        "equity_history": [],
                        "logs": [],
                        "latest_candles": {}
                    }
                }

                # 0. Portfolio Metrics (Needed for allocation calcs)
                total_value = float(await state.get_float("portfolio:total_value") or float(os.getenv("CAPITAL", 10000.0)))
                
                # 1. Market Data (Top 10 only for WS to save bandwidth, or all if needed)
                market_data = {}
                display_symbols = SYMBOLS[:10] # Dashboard only needs top 10 real-time
                for symbol in display_symbols:
                    price = float(await state.get_float(f"price:{symbol}") or 0.0)
                    change_24h = 0.0
                    df_24h = await state.get_df(f"ohlcv:1h:{symbol}", n=24)
                    if df_24h is not None and not df_24h.empty:
                        open_24h = float(df_24h.iloc[0]['close'])
                        if open_24h > 0:
                            change_24h = ((price - open_24h) / open_24h) * 100
                    
                    # Get ML prediction details
                    ml_data = await state.get(f"ml_signal:{symbol}") or {}
                    if isinstance(ml_data, str):
                        try: ml_data = json.loads(ml_data)
                        except: ml_data = {}
                    
                    market_data[symbol] = {
                        "price": price,
                        "change": change_24h,
                        "funding": float(await state.get_float(f"funding:{symbol}") or 0.0),
                        "signal": ml_data.get('signal', 'NEUTRAL'),
                        "confidence": ml_data.get('confidence', 0.0) * 100, 
                    }
                payload["data"]["market"] = market_data
                
                # 1.1 Sector Heatmap
                from core.portfolio_risk_manager import PortfolioRiskManager
                risk_mgr = PortfolioRiskManager(None) # Lightweight for sector mapping
                sector_heat = {}
                active_positions = await state.get("positions:active") or []
                for pos in active_positions:
                    sec = risk_mgr.get_symbol_sector(pos['symbol'])
                    sector_heat[sec] = sector_heat.get(sec, 0.0) + float(pos.get('notional', 0.0))
                payload["data"]["sector_heat"] = sector_heat
                
                # Signal Heatmap (mock or real distribution)
                payload["data"]["signal_heatmap"] = await state.get("ml:signal_heatmap") or []
                
                # 2. Strategy Stats
                strategies = {}
                for s in ["scalper", "swing", "position", "ai_ensemble"]:
                    pos_count = int(await state.get(f"stats:{s}:pos_count") or 0)
                    pnl = float(await state.get_float(f"stats:{s}:pnl") or 0.0)
                    trades = int(await state.get(f"stats:{s}:trades") or 0)
                    wins = int(await state.get(f"stats:{s}:wins") or 0)
                    win_rate = (wins / trades * 100) if trades > 0 else 0.0
                    
                    # Get allocation from config
                    allocation_pct = STRATEGY_ALLOCATIONS.get(s, 0.10)
                    allocated_capital = total_value * allocation_pct
                    
                    strategies[s] = {
                        "pos_count": pos_count,
                        "pnl": pnl,
                        "win_rate": win_rate,
                        "trades": trades,
                        "active_positions": pos_count,
                        "status": await state.get(f"engine:status:{s}") or ("ACTIVE" if pos_count > 0 else "SCANNING"),
                        "allocated": 0, # To be computed 
                        "avg_hold": "N/A",
                        "last_trade": "N/A"
                    }
                payload["data"]["strategies"] = strategies
                
                # 3. Portfolio Metrics (Already fetched above)
                sharpe = float(await state.get_float("metrics:sharpe") or 0.0)
                drawdown = float(await state.get_float("metrics:drawdown") or 0.0)
                win_rate = float(await state.get_float("metrics:winrate") or 0.0)
                daily_pnl = float(await state.get_float('pnl:24h') or 0.0)
                
                # Derive sentiment from BTC signal
                btc_sig = market_data.get("BTC/USDT", {}).get("signal", "NEUTRAL")
                sentiment = "NEUTRAL"
                if btc_sig == "BUY": sentiment = "BULL"
                elif btc_sig == "SELL": sentiment = "BEAR"

                payload["data"]["portfolio"] = {
                    "total_value": total_value,
                    "daily_pnl": daily_pnl,
                    "daily_change_pct": ((daily_pnl / total_value) * 100) if total_value > 0 else 0.0,
                    "sharpe": sharpe,
                    "drawdown": drawdown,
                    "win_rate": win_rate,
                    "profit_factor": float(await state.get_float("metrics:profit_factor") or 1.0),
                    "sentiment": sentiment,
                    "volatility": 4.2
                }
                
                # 3.1 Status
                payload["data"]["status"] = await state.get('engine:status') or 'ACTIVE'
                
                # 4. Open Positions
                payload["data"]["positions"] = await state.get("positions:active") or []
                
                # 4.1 Active Orders from Binance
                binance_acc = await state.get('binance:account') or {}
                payload["data"]["orders"] = binance_acc.get('positions', []) # Simplified for now
                
                # 5. Recent Signals
                signals_raw = await state.redis.lrange('signals:history', 0, 49)
                payload["data"]["signals"] = [json.loads(s) for s in signals_raw]
                
                # 5.1 Trade History
                trades_raw = await state.redis.lrange('trade:history', 0, 49)
                payload["data"]["trades"] = [json.loads(t) for t in trades_raw]
                
                # 6. Equity History
                equity_raw = await state.redis.lrange('equity:history', 0, 49)
                payload["data"]["equity_history"] = [json.loads(e) for e in equity_raw]
                
                # 7. Recent Logs
                logs_raw = await state.redis.lrange('logs:live', 0, 99)
                payload["data"]["logs"] = [json.loads(l) for l in logs_raw]
                
                # 8. Latest Candles (Shortcut for Main Chart)
                payload["data"]["latest_candles"] = market_data["BTC/USDT"]["candles"]
                
                # 9. Rollout Status
                rollout_phase = await state.get('rollout:current_phase') or 'PHASE_1_MICRO'
                rollout_start = await state.get_float('rollout:phase_start_time') or 0.0
                elapsed_days = round((time.time() - rollout_start) / 86400, 1) if rollout_start > 0 else 0
                
                # Send METRICS_UPDATE for legacy compatibility if needed
                await websocket.send_json({
                    "type": "METRICS_UPDATE",
                    "data": {
                        "account_value": total_value,
                        "daily_pnl": float(await state.get_float('pnl:24h') or 0.0),
                        "win_rate": win_rate,
                        "drawdown": drawdown,
                        "phase": rollout_phase
                    }
                })

                # Broadcast rollout update
                await websocket.send_json({
                    "type": "ROLLOUT_UPDATE",
                    "phase": rollout_phase,
                    "elapsed_days": elapsed_days
                })

                # Send rich payload
                await websocket.send_json(payload)
                
                await asyncio.sleep(1)  # High frequency 1s update
                
        except WebSocketDisconnect:
            log.info("🛑 Dashboard WS disconnected")
        except Exception as e:
            log.error(f"❌ WebSocket error: {e}")

    # --- DASHBOARD SERVING (Hardened) ---
    import os
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    dist_path = os.path.join(base_dir, "dashboard", "dist")
    
    if os.path.exists(dist_path):
        log.info(f"📁 Mounting Dashboard from {dist_path}")
        
        # Explicit root handler with cache-busting
        @app.get("/")
        async def serve_index():
            return FileResponse(
                os.path.join(dist_path, "index.html"),
                headers={"Cache-Control": "no-cache, no-store, must-revalidate"}
            )

        app.mount("/", StaticFiles(directory=dist_path, html=True), name="static")

        # Fallback for SPA Routing (React Router)
        @app.exception_handler(404)
        async def spa_fallback(request, __):
            return FileResponse(
                os.path.join(dist_path, "index.html"),
                headers={"Cache-Control": "no-cache, no-store, must-revalidate"}
            )
    else:
        log.warning(f"⚠️ Dashboard dist folder not found at {dist_path}")
    
    return app
