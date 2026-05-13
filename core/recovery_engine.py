import logging
import asyncio
import os
import json
import ccxt.async_support as ccxt
import pandas as pd
from datetime import datetime, timezone
from typing import Dict, List, Any

log = logging.getLogger("RecoveryEngine")

class RecoveryEngine:
    """
    Handles 'Gap Recovery' when the bot starts after being offline.
    Ensures trade state is consistent with what happened in the real market.
    """
    
    HEARTBEAT_FILE = "heartbeat.json"
    
    def __init__(self, state_manager, risk_manager):
        self.state = state_manager
        self.risk  = risk_manager
        self.exchange = ccxt.binance({"enableRateLimit": True})

    async def run_recovery_sequence(self):
        """Main entry point for boot-time recovery."""
        log.info("🚀 Starting Recovery Sequence...")
        
        # 1. Detect Gap
        last_heartbeat = self._get_last_heartbeat()
        if not last_heartbeat:
            log.info("ℹ️ No previous heartbeat found. First run or clean state.")
            self._save_heartbeat()
            return

        now = int(datetime.now(timezone.utc).timestamp() * 1000)
        gap_ms = now - last_heartbeat
        
        if gap_ms < 60000: # Less than 1 minute gap
            log.info("✅ Negligible gap detected (< 1 min).")
            return

        gap_mins = gap_ms // 60000
        log.warning(f"⚠️ GAP DETECTED: {gap_mins} minutes offline.")

        # 2. Find Active Trades
        active_positions = await self.state.get_all_positions()
        if not active_positions:
            log.info("✅ No active positions to recover.")
            self._save_heartbeat()
            return

        log.info(f"🔍 Replaying {len(active_positions)} active positions through gap...")

        # 3. Fetch & Replay for each position
        for symbol, pos in active_positions.items():
            await self._recover_position(symbol, pos, last_heartbeat, now)

        # 4. Save new heartbeat
        self._save_heartbeat()
        log.info("✅ Recovery Sequence Complete.")

    def _get_last_heartbeat(self) -> int | None:
        if os.path.exists(self.HEARTBEAT_FILE):
            try:
                with open(self.HEARTBEAT_FILE, 'r') as f:
                    data = json.load(f)
                    return data.get("timestamp")
            except Exception as e:
                log.error(f"Error reading heartbeat: {e}")
        return None

    def _save_heartbeat(self):
        now = int(datetime.now(timezone.utc).timestamp() * 1000)
        with open(self.HEARTBEAT_FILE, 'w') as f:
            json.dump({"timestamp": now, "time_str": str(datetime.now())}, f)

    async def _recover_position(self, symbol: str, pos: dict, start_ms: int, end_ms: int):
        """Downloads 1m data and replays it to check for exits."""
        try:
            log.info(f"📥 Fetching gap data for {symbol}...")
            # Fetch 1m candles for the gap
            ohlcv = await self.exchange.fetch_ohlcv(symbol, '1m', since=start_ms, limit=1440) # max 1 day at once
            if not ohlcv:
                return

            # Simulation Logic
            entry_price = pos.get("entry_price")
            side = pos.get("side")
            sl   = pos.get("sl")
            tp   = pos.get("tp")
            
            for candle in ohlcv:
                ts, o, h, l, c, v = candle
                
                hit_exit = False
                exit_price = 0
                exit_reason = ""
                exit_time = ts

                if side == "LONG":
                    # Check SL hit
                    if l <= sl:
                        hit_exit = True
                        exit_price = sl
                        exit_reason = "STOP_LOSS (Offline)"
                    # Check TP hit
                    elif h >= tp:
                        hit_exit = True
                        exit_price = tp
                        exit_reason = "TAKE_PROFIT (Offline)"
                else: # SHORT
                    # Check SL hit
                    if h >= sl:
                        hit_exit = True
                        exit_price = sl
                        exit_reason = "STOP_LOSS (Offline)"
                    # Check TP hit
                    elif l <= tp:
                        hit_exit = True
                        exit_price = tp
                        exit_reason = "TAKE_PROFIT (Offline)"

                if hit_exit:
                    log.warning(f"💥 {symbol} {exit_reason} at {exit_price} during gap!")
                    await self._settle_offline_trade(symbol, pos, exit_price, exit_reason, exit_time)
                    return # Stop simulation for this asset

            log.info(f"✅ {symbol} survived the gap.")

        except Exception as e:
            log.error(f"Error recovering {symbol}: {e}")

    async def _settle_offline_trade(self, symbol: str, pos: dict, exit_price: float, reason: str, timestamp: int):
        """Removes the trade from active and logs the historical PnL."""
        # 1. Calculate PnL
        entry = pos["entry_price"]
        side  = pos["side"]
        qty   = pos["qty"]
        
        if side == "LONG":
            pnl_pct = (exit_price - entry) / entry
        else:
            pnl_pct = (entry - exit_price) / entry
            
        pnl_val = pnl_pct * (entry * qty)
        
        log.info(f"💰 Settling {symbol}: PnL {pnl_pct:.2%} (${pnl_val:.2f})")
        
        # 2. Update state (Remove from active, add to history)
        # Note: In a real system, we'd also sync with the exchange to verify if orders actually filled.
        # For this local simulation, we assume our internal SL/TP was the source of truth.
        
        history_entry = {
            "symbol": symbol,
            "side": side,
            "entry": entry,
            "exit": exit_price,
            "pnl_pct": pnl_pct,
            "pnl_val": pnl_val,
            "reason": reason,
            "closed_at": timestamp
        }
        
        await self.state.delete(f"position:{symbol}")
        # Add to history list in Redis/LocalDB
        history = await self.state.get("trade_history") or []
        history.append(history_entry)
        await self.state.set("trade_history", history)
        
        # 3. Update balance
        balance = await self.state.get_float("portfolio:balance") or 10000.0
        await self.state.set("portfolio:balance", balance + pnl_val)

    async def close(self):
        await self.exchange.close()
