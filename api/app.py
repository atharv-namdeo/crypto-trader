import json
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Body
from fastapi.middleware.cors import CORSMiddleware
import asyncio
import logging
from core.state_manager import StateManager

log = logging.getLogger("FastAPI")

def create_app(state: StateManager):
    app = FastAPI(title="Quant Engine API", version="5.0")

    app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

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
        stats = {}
        for s in ["scalper", "swing", "position", "ai_ensemble"]:
            stats[s] = {
                "trades": int(await state.get(f"stats:{s}:trades") or 0),
                "wins": int(await state.get(f"stats:{s}:wins") or 0),
                "pnl": float(await state.get(f"stats:{s}:pnl") or 0.0),
                "pos_count": len(await state.redis.keys(f"{s}:pos:*"))
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
                payload = {"type": "engine_update", "data": {}}
                
                # 1. Market Data
                market_data = {}
                for symbol in ["BTC/USDT", "ETH/USDT"]:
                    s_clean = symbol.replace("/", "")
                    market_data[symbol] = {
                        "price": float(await state.get_float(f"price:{symbol}") or 0.0),
                        "funding": float(await state.get_float(f"funding:{symbol}") or 0.0),
                        "fuzzy": await state.get(f"fuzzy_scores:{symbol}") or {},
                        "candles": {
                            tf: (await state.get_df(f"ohlcv:{tf}:{symbol}", n=1)).to_dict(orient='records') if await state.redis.exists(f"ohlcv:{tf}:{symbol}") else []
                            for tf in ["1m", "5m", "15m", "1h", "4h"]
                        }
                    }
                payload["data"]["market"] = market_data
                
                # Push latest candle to chart if needed
                payload["data"]["latest_candles"] = market_data["BTC/USDT"]["candles"]

                # 2. Strategy Stats
                stats = {}
                for s in ["scalper", "swing", "position", "ai_ensemble"]:
                    stats[s] = {
                        "trades": int(await state.get(f"stats:{s}:trades") or 0),
                        "wins": int(await state.get(f"stats:{s}:wins") or 0),
                        "pnl": float(await state.get(f"stats:{s}:pnl") or 0.0),
                        "pos_count": len(await state.redis.keys(f"{s}:pos:*"))
                    }
                payload["data"]["strategies"] = stats

                # 3. Portfolio & Metrics
                payload["data"]["portfolio"] = await state.get_float('portfolio:value') or 0.0
                payload["data"]["metrics"] = {
                    "sharpe": float(await state.get('metrics:sharpe') or 0),
                    "drawdown": float(await state.get('metrics:drawdown') or 0),
                    "pf": float(await state.get('metrics:profit_factor') or 0),
                    "winrate": float(await state.get('metrics:winrate') or 0)
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

                await websocket.send_json(payload)
                await asyncio.sleep(2)
                
        except WebSocketDisconnect:
            log.info("Dashboard WS disconnected")
        except Exception as e:
            log.error(f"WS push error: {e}")

    return app
