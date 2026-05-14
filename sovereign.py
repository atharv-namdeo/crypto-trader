import asyncio
import logging
import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from datetime import datetime, timezone
import ccxt # Use sync CCXT for better stability on Windows
import pandas as pd
import json

from core.data.state import StateManager
from core.risk.manager import RiskManager
from core.strategies.ensemble import EnsembleAlgorithm
from core.data.recovery import RecoveryEngine

# Logging Setup
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
log = logging.getLogger("SovereignLive")

app = FastAPI(title="Sovereign Quant API")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global State
state = StateManager()
risk  = RiskManager()
engine = None 

@app.get("/status")
async def get_status():
    balance = await state.get_float("portfolio:balance") or 10000.0
    positions = await state.get_all_positions()
    signals = {}
    for s in ['BTC/USDT', 'ETH/USDT', 'SOL/USDT', 'XRP/USDT', 'ADA/USDT', 'DOGE/USDT', 'SHIB/USDT', 'AVAX/USDT', 'LINK/USDT']:
        sig = await state.firebase.get(f"trading/signals/{s}")
        if sig: signals[s] = sig

    return {
        "status": "Running",
        "phase": "Phase 11: Omega Brain",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "balance": balance,
        "active_trades": len(positions),
        "positions": positions,
        "signals": signals
    }

@app.get("/history")
async def get_history():
    history = await state.get("trade_history") or []
    return history[-100:]

@app.post("/strategy/check")
async def force_strategy_check():
    log.info("🎯 Manual Strategy Check Triggered.")
    asyncio.create_task(run_full_evaluation())
    return {"status": "Evaluation started"}

async def run_full_evaluation():
    # Helper to run sync work in thread
    loop = asyncio.get_event_loop()
    await loop.run_in_executor(None, sync_evaluation)

def sync_evaluation():
    ex = ccxt.binance({"enableRateLimit": True, "timeout": 20000})
    symbols = ['BTC/USDT', 'ETH/USDT', 'SOL/USDT', 'XRP/USDT', 'ADA/USDT', 'DOGE/USDT', 'SHIB/USDT', 'AVAX/USDT', 'LINK/USDT']
    try:
        ex.load_markets()
        for symbol in symbols:
            sync_process_symbol(symbol, ex)
    except Exception as e:
        log.error(f"Sync Eval Error: {e}")
    finally:
        # ccxt sync doesn't strictly need close but good practice
        pass

def sync_process_symbol(symbol, ex):
    """Stub for sync evaluation logic if needed."""
    pass

# --- REFACTORING TO HYBRID ---

async def trading_loop():
    global engine
    log.info("💎 Sovereign Trading Loop Started (Sync-Hybrid Mode).")
    
    await state.connect()
    engine = EnsembleAlgorithm(state)
    
    # 1. Recovery
    recovery = RecoveryEngine(state, risk)
    await recovery.run_recovery_sequence()
    await recovery.close()
    
    ex = ccxt.binance({"enableRateLimit": True, "timeout": 20000})
    symbols = ['BTC/USDT', 'ETH/USDT', 'SOL/USDT', 'XRP/USDT', 'ADA/USDT', 'DOGE/USDT', 'SHIB/USDT', 'AVAX/USDT', 'LINK/USDT']
    
    last_hour = -1

    while True:
        try:
            now = datetime.now(timezone.utc)
            
            # Heartbeat
            with open("heartbeat.json", 'w') as f:
                json.dump({"timestamp": int(now.timestamp() * 1000), "time_str": str(now)}, f)

            # Strategy Check
            if now.hour != last_hour:
                log.info(f"🕒 Hour transition ({now.hour}:00). Running Ensemble...")
                for symbol in symbols:
                    await process_symbol_hybrid(symbol, ex)
                last_hour = now.hour

            # Real-time Tracking
            active_positions = await state.get_all_positions()
            if active_positions:
                for symbol, pos in active_positions.items():
                    # Use run_in_executor for the sync fetch_ticker
                    ticker = await asyncio.get_event_loop().run_in_executor(None, ex.fetch_ticker, symbol)
                    await track_position(symbol, pos, ticker['last'])

            await asyncio.sleep(20)

        except Exception as e:
            log.error(f"Loop Error: {e}")
            await asyncio.sleep(10)

async def process_symbol_hybrid(symbol, ex):
    try:
        loop = asyncio.get_event_loop()
        # Fetch data in thread
        data = await loop.run_in_executor(None, fetch_mtf_sync, symbol, ex)
        
        # Save to state
        await state.set_df(f"ohlcv:1h:{symbol}", pd.DataFrame(data['1h'], columns=['timestamp', 'open', 'high', 'low', 'close', 'volume']))
        await state.set_df(f"ohlcv:1d:{symbol}", pd.DataFrame(data['1d'], columns=['timestamp', 'open', 'high', 'low', 'close', 'volume']))
        await state.set_df(f"ohlcv:1m:{symbol}", pd.DataFrame(data['1m'], columns=['timestamp', 'open', 'high', 'low', 'close', 'volume']))
        
        signal = await engine.generate_signal(symbol)
        
        if signal["action"] in ("BUY", "SELL"):
            log.info(f"🚀 SIGNAL: {symbol} {signal['action']} | Conf: {signal['confidence']:.2f}")
            ticker = await loop.run_in_executor(None, ex.fetch_ticker, symbol)
            await execute_signal_fixed(symbol, signal, ticker['last'])
        else:
            log.info(f"ℹ️ {symbol} Neutral ({signal['action']}) | {signal.get('reason', '')}")

    except Exception as e:
        log.error(f"Process Error {symbol}: {e}")

def fetch_mtf_sync(symbol, ex):
    return {
        '1h': ex.fetch_ohlcv(symbol, '1h', limit=200),
        '1d': ex.fetch_ohlcv(symbol, '1d', limit=250),
        '1m': ex.fetch_ohlcv(symbol, '1m', limit=100)
    }

async def execute_signal_fixed(symbol, signal, price):
    balance = await state.get_float("portfolio:balance") or 10000.0
    atr = signal.get("atr", price * 0.02)
    size_info = await risk.compute_position_size(balance, price, atr)
    
    if size_info["qty"] <= 0: return

    stops = risk.calculate_adaptive_stops(price, atr, signal.get("regime", "BULL"), signal["action"])
    
    position = {
        "symbol": symbol,
        "side": "LONG" if signal["action"] == "BUY" else "SHORT",
        "entry_price": price,
        "qty": size_info["qty"],
        "sl": stops["stop"],
        "tp": stops["tp"],
        "thinking": signal.get("metadata", {}),
        "opened_at": int(datetime.now(timezone.utc).timestamp() * 1000)
    }
    await state.set_position(symbol, position)
    log.info(f"✅ POSITION OPENED: {symbol} @ {price}")

async def track_position(symbol, pos, current_price):
    side, sl, tp = pos["side"], pos["sl"], pos["tp"]
    hit = False
    if side == "LONG":
        if current_price <= sl: hit, reason = True, "STOP_LOSS"
        elif current_price >= tp: hit, reason = True, "TAKE_PROFIT"
    else:
        if current_price >= sl: hit, reason = True, "STOP_LOSS"
        elif current_price <= tp: hit, reason = True, "TAKE_PROFIT"
        
    if hit:
        log.info(f"💥 {symbol} hit {reason} @ {current_price}")
        
        # Calculate PnL
        qty = pos["qty"]
        entry = pos["entry_price"]
        if side == "LONG":
            raw_pnl = (current_price - entry) * qty
        else:
            raw_pnl = (entry - current_price) * qty
            
        # Update Balance
        balance = await state.get_float("portfolio:balance") or 10000.0
        new_balance = balance + raw_pnl
        await state.set("portfolio:balance", new_balance)
        
        # Record History
        trade_record = {
            "symbol": symbol,
            "side": side,
            "entry": entry,
            "exit": current_price,
            "qty": qty,
            "pnl": raw_pnl,
            "pnl_pct": (raw_pnl / (entry * qty)) * 100,
            "reason": reason,
            "closed_at": int(datetime.now(timezone.utc).timestamp() * 1000)
        }
        history = await state.get("trade:history") or []
        history.append(trade_record)
        await state.set("trade:history", history)
        
        await state.remove_position(symbol)
        log.info(f"💰 {symbol} CLOSED. PnL: {raw_pnl:.2f} | New Balance: {new_balance:.2f}")

async def main():
    api_task = asyncio.create_task(asyncio.to_thread(uvicorn.run, app, host="0.0.0.0", port=8000))
    trade_task = asyncio.create_task(trading_loop())
    await asyncio.gather(api_task, trade_task)

if __name__ == "__main__":
    asyncio.run(main())
