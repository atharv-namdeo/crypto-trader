import json
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Body
from fastapi.middleware.cors import CORSMiddleware
import asyncio
import logging
import time
from datetime import datetime
from core.state_manager import StateManager
from api.metrics import router as metrics_router

from security.production_hardening import setup_production_security

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

    @app.post("/api/v1/order")
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

    @app.post("/api/v1/settings")
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
        log.info(f"Dashboard WS connected")
        try:
            while True:
                if not state.redis:
                    await websocket.send_json({"type": "info", "data": "Waiting for Redis..."})
                    await asyncio.sleep(5)
                    continue

                payload = {"type": "engine_update", "data": {}}
                
                # 1. Market Data
                market_data = {}
                for symbol in ["BTC/USDT", "ETH/USDT"]:
                    price = float(await state.get_float(f"price:{symbol}") or 0.0)
                    
                    # Calculate 24h change
                    change_24h = 0.0
                    df_24h = await state.get_df(f"ohlcv:1h:{symbol}", n=24)
                    if df_24h is not None and not df_24h.empty:
                        open_24h = float(df_24h.iloc[0]['close'])
                        if open_24h > 0:
                            change_24h = ((price - open_24h) / open_24h) * 100
                            
                    market_data[symbol] = {
                        "price": price,
                        "change": change_24h,
                        "funding": float(await state.get_float(f"funding:{symbol}") or 0.0),
                        "fuzzy": await state.get(f"fuzzy_scores:{symbol}") or {},
                        "candles": {
                            tf: (await state.get_df(f"ohlcv:{tf}:{symbol}", n=1)).to_dict(orient='records') if (state.redis and await state.redis.exists(f"ohlcv:{tf}:{symbol}")) else []
                            for tf in ["1m", "5m", "15m", "1h", "4h"]
                        }
                    }
                    
                    # 1.1 ML Ensemble Signals
                    ml_sig = await state.get(f"ml_signal:{symbol}")
                    if ml_sig:
                        if isinstance(ml_sig, str):
                            try: ml_sig = json.loads(ml_sig)
                            except: pass
                        
                        # Send as separate message for the MLSignalPanel component
                        await websocket.send_json({
                            "type": "ML_UPDATE",
                            "symbol": symbol,
                            "signal": ml_sig.get('signal'),
                            "confidence": ml_sig.get('confidence'),
                            "latency": ml_sig.get('latency', 84) # fallback
                        })
                payload["data"]["market"] = market_data
                
                # 1.2 Signal Quality History
                sq_history = await state.redis.lrange('signal_quality:history', 0, 0)
                if sq_history:
                    sq = json.loads(sq_history[0])
                    await websocket.send_json({
                        "type": "SIGNAL_QUALITY",
                        "symbol": sq['symbol'] if 'symbol' in sq else "BTC/USDT",
                        "accuracy": sq['accuracy']
                    })
                
                # 1.3 Rollout Status
                rollout_phase = await state.get('rollout:current_phase') or 'PHASE_1_MICRO'
                rollout_start = await state.get_float('rollout:phase_start_time') or 0.0
                await websocket.send_json({
                    "type": "ROLLOUT_UPDATE",
                    "phase": rollout_phase,
                    "elapsed_days": round((time.time() - rollout_start) / 86400, 1) if rollout_start > 0 else 0
                })
                
                # Push latest candle to chart if needed
                payload["data"]["latest_candles"] = market_data["BTC/USDT"]["candles"]

                # 2. Strategy Stats
                stats = {}
                for s in ["scalper", "swing", "position", "ai_ensemble"]:
                    # pos_count: Count active position keys in Redis
                    pos_keys = await state.redis.keys(f"{s}:pos:*") if state.redis else []
                    stats[s] = {
                        "trades": int(await state.get(f"stats:{s}:trades") or 0),
                        "wins": int(await state.get(f"stats:{s}:wins") or 0),
                        "pnl": float(await state.get(f"stats:{s}:pnl") or 0.0),
                        "pos_count": len(pos_keys),
                        "status": "ACTIVE" if pos_keys else "SCANNING"
                    }
                payload["data"]["strategies"] = stats

                # 3. Portfolio & Metrics
                # Get ensemble sentiment for BTC
                ens_sig = await state.get("ml_signal:BTC/USDT")
                sentiment = "NEUTRAL"
                if ens_sig:
                    if isinstance(ens_sig, str):
                        try: ens_sig = json.loads(ens_sig)
                        except: pass
                    raw_sentiment = ens_sig.get('signal', 'NEUTRAL')
                    if raw_sentiment == 'BUY': sentiment = 'BULL'
                    elif raw_sentiment == 'SELL': sentiment = 'BEAR'
                    else: sentiment = 'NEUTRAL'

                payload["data"]["portfolio"] = {
                    "value": float(await state.get_float('portfolio:value') or 0.0),
                    "sharpe": float(await state.get('metrics:sharpe') or 0),
                    "drawdown": float(await state.get('metrics:drawdown') or 0),
                    "profit_factor": float(await state.get('metrics:profit_factor') or 0),
                    "win_rate": float(await state.get('metrics:winrate') or 0),
                    "sentiment": sentiment
                }

                # 4. History (last 20 items to save bandwidth)
                equity_raw = await state.redis.lrange('equity:history', 0, 19)
                payload["data"]["equity_history"] = [json.loads(e) for e in equity_raw]
                
                logs_raw = await state.redis.lrange('logs:live', 0, 49)
                payload["data"]["logs"] = [json.loads(l) for l in logs_raw]

                # 5. Open Positions
                payload["data"]["positions"] = await state.get_all_positions()

                # 6. Signals for Chart (Entries/Exits)
                signals_raw = await state.redis.lrange('signals:history', 0, 49)
                payload["data"]["signals"] = [json.loads(s) for s in signals_raw]
                
                # 7. METRICS_UPDATE for Live Dashboard
                await websocket.send_json({
                    "type": "METRICS_UPDATE",
                    "data": {
                        "account_value": payload["data"]["portfolio"]["value"],
                        "daily_pnl": float(await state.get_float('pnl:24h') or 0.0),
                        "win_rate": payload["data"]["portfolio"]["win_rate"],
                        "drawdown": payload["data"]["portfolio"]["drawdown"],
                        "phase": rollout_phase
                    }
                })
                
                # 8. Latest Trade Executed
                latest_trade = await state.redis.lrange('trade:history', 0, 0)
                if latest_trade:
                    await websocket.send_json({
                        "type": "TRADE_EXECUTED",
                        "timestamp": datetime.now().isoformat(),
                        "data": json.loads(latest_trade[0])
                    })

                await websocket.send_json(payload)
                await asyncio.sleep(2)
                
        except WebSocketDisconnect:
            log.info("Dashboard WS disconnected")
        except Exception as e:
            log.error(f"WS push error: {e}")

    return app
