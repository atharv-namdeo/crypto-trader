"""
api/app.py
FastAPI server serving dashboard real-time data — Phase 2
"""

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
import asyncio
import logging
from core.state_manager import StateManager

log = logging.getLogger("FastAPI")

def create_app(state: StateManager):
    app = FastAPI(title="Quant Engine API", version="4.0")

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/api/v1/health")
    async def get_health():
        return {"status": "ok", "redis": state.redis is not None}

    @app.get("/api/v1/signals")
    async def get_signals():
        signals = {}
        for symbol in ["BTCUSDT", "ETHUSDT"]:
            signals[symbol] = {
                "ensemble": await state.get(f"ensemble:{symbol}"),
                "regime": await state.get(f"regime:{symbol}"),
            }
        return {"data": signals}

    @app.get("/api/v1/positions")
    async def get_positions():
        positions = await state.get_all_positions()
        return {"data": positions}

    @app.websocket("/ws")
    async def websocket_endpoint(websocket: WebSocket):
        await websocket.accept()
        log.info(f"Dashboard WS connected: {websocket.client}")
        try:
            while True:
                data = {}
                for symbol in ["BTCUSDT", "ETHUSDT"]:
                    data[symbol] = {
                        "ensemble": await state.get(f"ensemble:{symbol}"),
                        "position": await state.get(f"position:{symbol}"),
                        "price": await float(state.get_float(f"price:{symbol}") or 0.0),
                        "features": await state.get(f"features:{symbol}")
                    }
                data["risk"] = await state.get("risk_state")
                
                await websocket.send_json({"type": "engine_update", "data": data})
                await asyncio.sleep(2)  # Push every 2 seconds
                
        except WebSocketDisconnect:
            log.info(f"Dashboard WS disconnected: {websocket.client}")
        except Exception as e:
            log.error(f"WS push error: {e}")

    return app
