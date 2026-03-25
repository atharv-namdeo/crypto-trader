import json
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Body, Depends
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from starlette.responses import FileResponse
import asyncio
import logging
import time
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
        settings = {}
        for key in ["scalper_enabled", "scalper_threshold", "swing_enabled", "swing_threshold", "position_enabled", "position_threshold"]:
            settings[key] = await state.get(f"settings:{key}")
        return {"data": settings}

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
        
        try:
            while True:
                if not state.redis:
                    await websocket.send_json({"type": "info", "data": "Waiting for Redis..."})
                    await asyncio.sleep(5)
                    continue

                payload = {"type": "engine_update", "data": {}}
                
                # 1. Market Data
                market_data = {}
                for symbol in ["BTC/USDT", "ETH/USDT", "SOL/USDT"]:
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
                        "fuzzy": await state.get(f"fuzzy_scores:{symbol}") or {},
                        "signal": ml_data.get('signal', 'NEUTRAL'),
                        "confidence": ml_data.get('confidence', 0.0) * 100, # Convert to pct
                        "candles": {
                            tf: (await state.get_df(f"ohlcv:{tf}:{symbol}", n=1)).to_dict(orient='records') 
                            if (state.redis and await state.redis.exists(f"ohlcv:{tf}:{symbol}")) else []
                            for tf in ["1m", "5m", "15m", "1h", "4h"]
                        }
                    }
                payload["data"]["market"] = market_data
                
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
                    
                    strategies[s] = {
                        "pos_count": pos_count,
                        "pnl": pnl,
                        "win_rate": win_rate,
                        "trades": trades,
                        "status": "ACTIVE" if pos_count > 0 else "SCANNING"
                    }
                payload["data"]["strategies"] = strategies
                
                # 3. Portfolio Metrics
                total_value = float(await state.get_float("portfolio:total_value") or float(os.getenv("CAPITAL", 10000.0)))
                sharpe = float(await state.get_float("metrics:sharpe") or 0.0)
                drawdown = float(await state.get_float("metrics:drawdown") or 0.0)
                win_rate = float(await state.get_float("metrics:winrate") or 0.0)
                
                # Derive sentiment from BTC signal
                btc_sig = market_data.get("BTC/USDT", {}).get("signal", "NEUTRAL")
                sentiment = "NEUTRAL"
                if btc_sig == "BUY": sentiment = "BULL"
                elif btc_sig == "SELL": sentiment = "BEAR"

                payload["data"]["portfolio"] = {
                    "value": total_value,
                    "sharpe": sharpe,
                    "drawdown": drawdown,
                    "win_rate": win_rate,
                    "profit_factor": float(await state.get_float("metrics:profit_factor") or 1.0),
                    "sentiment": sentiment,
                    "volatility": 4.2, # Placeholder or calc
                    "trades": int(await state.get("stats:total_trades") or sum(s['trades'] for s in strategies.values()))
                }
                
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

    # --- DASHBOARD SERVING ---
    import os
    if os.path.exists("dashboard/dist"):
        app.mount("/", StaticFiles(directory="dashboard/dist", html=True), name="static")

        # Fallback for SPA Routing (React Router)
        @app.exception_handler(404)
        async def spa_fallback(request, __):
            return FileResponse("dashboard/dist/index.html")
    
    return app
