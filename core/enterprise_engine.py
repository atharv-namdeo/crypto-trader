import asyncio
import logging
from datetime import datetime
from typing import List, Dict, Any

from core.state_manager import StateManager
from core.strategies.ensemble_algorithm import EnsembleAlgorithm
from execution.order_engine import OrderEngine
from config import SYMBOLS

log = logging.getLogger("EnterpriseEngine")


# ---------------------------------------------------------------------------
# Pre-trade validation helpers
# ---------------------------------------------------------------------------

async def _validate_signal_quality(
    symbol: str,
    signal: Dict[str, Any],
    state: StateManager,
) -> tuple:
    """
    Multi-layer pre-trade gate.
    Returns (allowed: bool, reason: str).

    Checks:
    1. Minimum 2 signal confirmations across timeframes
    2. Liquidity ($1M daily volume)
    3. Extreme-volatility guard (> 10% hourly move)
    4. EMA trend alignment (price > EMA20 > EMA50 for longs)
    5. Consecutive-loss throttle per strategy
    """
    action = signal.get("action", "NEUTRAL")
    if action not in ("BUY", "SELL"):
        return False, "non-directional signal"

    # 1. Minimum confirmations
    components = signal.get("components", {})
    votes = sum(
        1 for c in components.values()
        if c.get("action") == action
    )
    if votes < 2:
        return False, f"only {votes}/2 confirmations"

    # 2. Liquidity: use cached 24h volume (set by MultiAssetDataManager)
    vol_24h = await state.get_float(f"volume24h:{symbol}") or 0
    if 0 < vol_24h < 1_000_000:
        return False, f"volume ${vol_24h:,.0f} < $1M"

    # 3. Extreme volatility: compare last two 1h candles
    df_1h = await state.get_df(f"ohlcv:1h:{symbol}", n=5)
    if df_1h is not None and len(df_1h) >= 2:
        last_close = float(df_1h["close"].iloc[-1])
        prev_close = float(df_1h["close"].iloc[-2])
        hourly_move = abs(last_close - prev_close) / (prev_close + 1e-9)
        if hourly_move > 0.10:
            return False, f"hourly move {hourly_move:.1%} > 10%"

    # 4. EMA trend alignment
    if df_1h is not None and len(df_1h) >= 50:
        from core.utils import compute_ema
        closes = df_1h["close"]
        ema_20 = float(compute_ema(closes, 20).iloc[-1])
        ema_50 = float(compute_ema(closes, 50).iloc[-1])
        price = float(closes.iloc[-1])
        if action == "BUY" and not (price > ema_20 > ema_50):
            return False, "EMA trend not aligned for LONG"
        if action == "SELL" and not (price < ema_20 < ema_50):
            return False, "EMA trend not aligned for SHORT"

    # 5. Consecutive-loss throttle (strategy-level)
    strategy = signal.get("strategy", "ai_ensemble")
    consec = await state.get_float(f"metrics:{strategy}:consecutive_losses") or 0
    if consec >= 5:
        return False, f"{int(consec)} consecutive losses — throttled"

    return True, "ok"


async def _get_kelly_qty(
    strategy: str,
    capital: float,
    price: float,
    state: StateManager,
) -> float:
    """
    Quarter-Kelly position sizing from live trade history.
    Falls back to 2% of capital if insufficient history.
    """
    try:
        import json
        import numpy as np

        if not state.redis:
            return (capital * 0.02) / (price + 1e-9)

        history_raw = await state.redis.lrange("trade:history", 0, 99)
        all_trades = [json.loads(t) for t in (history_raw or [])]
        trades = [t for t in all_trades if t.get("strategy", "").lower() == strategy.lower()]

        if len(trades) < 10:
            return (capital * 0.015) / (price + 1e-9)

        pnls = [t.get("pnl_net", t.get("pnl", 0)) for t in trades]
        wins = [p for p in pnls if p > 0]
        losses = [p for p in pnls if p <= 0]

        if not losses:
            frac = 0.05
        elif not wins:
            frac = 0.01
        else:
            wr = len(wins) / len(pnls)
            rr = float(np.mean(wins)) / (abs(float(np.mean(losses))) + 1e-9)
            kelly = wr - ((1 - wr) / (rr + 1e-9))
            frac = max(0.01, min(0.05, kelly * 0.25))  # quarter-Kelly, 1–5%

        return (capital * frac) / (price + 1e-9)

    except Exception as exc:
        log.error(f"_get_kelly_qty error: {exc}")
        return (capital * 0.02) / (price + 1e-9)


class EnterpriseTradingEngine:
    """
    Orchestrates the 3-Layer Cloud Stack:
    Railway (Backend) <-> Firebase (DB) <-> Binance (Execution)

    Enhanced with:
    - Autonomous signal quality filters (confirmations, liquidity, volatility, EMA)
    - Kelly Criterion position sizing
    - Regime-aware stop-loss / take-profit via AdvancedRiskEngine
    """

    def __init__(self, state: StateManager, order_engine: OrderEngine):
        self.state = state
        self.order_engine = order_engine
        self.algorithm = EnsembleAlgorithm(state)
        self.running = False

    async def run_market_data_pump(self):
        """Continuously sync top symbol prices to Firebase."""
        log.info("📡 Starting Market Data Pump...")
        while self.running:
            try:
                for symbol in SYMBOLS[:20]: # Priority sync for top 20
                    price = await self.state.get_float(f"price:{symbol}")
                    if price:
                        # StateManager already mirrors price: keys, but we can add more rich data here
                        self.state.firebase.update(f"market/prices/{symbol}", {
                            "current_price": price,
                            "timestamp": int(datetime.utcnow().timestamp() * 1000)
                        })
                await asyncio.sleep(2) # 2s resolution for Firebase
            except Exception as e:
                log.error(f"Market pump error: {e}")
                await asyncio.sleep(5)

    async def run_signal_engine(self):
        """Generate high-conviction signals across multiple timeframes."""
        log.info("🧠 Starting Enterprise Signal Engine...")
        while self.running:
            try:
                tasks = [self.algorithm.generate_signal(s) for s in SYMBOLS]
                await asyncio.gather(*tasks)
                await asyncio.sleep(30) # Signal check every 30s
            except Exception as e:
                log.error(f"Signal engine error: {e}")
                await asyncio.sleep(10)

    async def run_execution_engine(self):
        """Monitor signals in Firebase and execute real orders on Binance."""
        log.info("⚖️ Starting Enterprise Execution Engine...")
        while self.running:
            try:
                capital = await self.state.get_float("portfolio:value") or 1000.0

                for symbol in SYMBOLS:
                    # Read the ground truth signal from Firebase
                    signal_data = self.state.firebase.get(f"trading/signals/{symbol}")

                    if not signal_data or signal_data.get("action") == "NEUTRAL":
                        continue

                    # Check for existing positions in Redis (hot state)
                    pos = await self.state.get_position(symbol)

                    # --- AUTONOMOUS SIGNAL QUALITY GATE ---
                    allowed, reason = await _validate_signal_quality(symbol, signal_data, self.state)

                    # 1. EXECUTE BUY
                    if signal_data["action"] == "BUY" and not pos:
                        if not allowed:
                            log.debug(f"[ENSEMBLE] {symbol} BUY rejected: {reason}")
                            continue

                        # Kelly-based quantity
                        price = await self.state.get_float(f"price:{symbol}") or signal_data.get("confidence", 1)
                        qty = await _get_kelly_qty("ai_ensemble", capital, price, self.state)

                        # Regime-aware stops
                        regime_data = await self.state.get(f"market:regime:{symbol}") or {}
                        regime = regime_data.get("regime", "NEUTRAL")
                        from advanced_risk_engine import AdvancedRiskEngine, REGIME_ATR_MULTIPLIERS
                        df_1h = await self.state.get_df(f"ohlcv:1h:{symbol}", n=20)
                        atr = price * 0.01
                        if df_1h is not None and len(df_1h) >= 14:
                            from core.utils import compute_atr
                            atr = float(compute_atr(df_1h, window=14).iloc[-1])
                        risk_engine = AdvancedRiskEngine(self.state)
                        stops = risk_engine.calculate_adaptive_stops(price, atr, regime, "LONG")

                        log.info(
                            f"🚀 [ENSEMBLE BUY] {symbol} | Conf={signal_data['confidence']:.2f} "
                            f"Qty={qty:.6f} SL={stops['sl']:.4f} TP={stops['tp']:.4f} Regime={regime}"
                        )
                        await self.state.set(f"order_request:{symbol}", {
                            "symbol": symbol,
                            "action": "OPEN",
                            "side": "LONG",
                            "qty": qty,
                            "price": price,
                            "sl": stops["sl"],
                            "tp": stops["tp"],
                            "strategy": "ai_ensemble",
                            "regime": regime,
                        })

                    # 2. EXECUTE SELL
                    elif signal_data["action"] == "SELL" and pos:
                        if not allowed:
                            log.debug(f"[ENSEMBLE] {symbol} SELL rejected: {reason}")
                            continue

                        log.info(f"🔥 [ENSEMBLE SELL] {symbol} | Conf: {signal_data['confidence']:.2f}")
                        await self.state.set(f"order_request:{symbol}", {
                            "symbol": symbol,
                            "action": "CLOSE",
                            "side": "LONG",
                            "qty": pos["qty"],
                            "strategy": "ai_ensemble",
                        })

                # Periodically sync all active orders to Firebase for dashboard
                if datetime.utcnow().second % 30 < 5:  # Sync every ~30s
                    active_orders = await self.order_engine.get_active_orders()
                    await self.state.set("orders:active", active_orders)

                await asyncio.sleep(5)  # Execution loop resolution
            except Exception as e:
                log.error(f"Execution engine error: {e}")
                await asyncio.sleep(10)

    async def start(self):
        self.running = True
        await asyncio.gather(
            self.run_market_data_pump(),
            self.run_signal_engine(),
            self.run_execution_engine()
        )

    def stop(self):
        self.running = False
