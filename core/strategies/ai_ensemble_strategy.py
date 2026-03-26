"""
AI Ensemble Strategy combining weighted neural network signals, anomaly gating, and technical indicators.
Based on: 
- Cohen & Aiche (2025): Weighted ensemble (FNN+LSTM+GRU) + RSI/MACD/Volume scoring.
- Alnami et al. (2025): Z-Score anomaly gating for volatility protection.
- Springer Chapter (2024): Optimizing for return-per-trade.
"""

import asyncio
import logging
import time
import json
import os
import traceback
import numpy as np
from core.state_manager import StateManager
from core.pnl_tracker import PnLTracker
from core.utils import compute_rsi, compute_atr, compute_adx, compute_ultosc, compute_ema
from ml.ensemble_model import EnsembleModel
from ml.anomaly_detector import AnomalyDetector
from core.risk import RiskManager
from config import SYMBOLS
from core.multi_strategy_manager import MultiStrategyManager

log = logging.getLogger("AIEnsemble")

class AIEnsembleStrategy:
    def __init__(self, state: StateManager, pnl_tracker: PnLTracker, manager: MultiStrategyManager):
        self.state = state
        self.pnl = pnl_tracker
        self.manager = manager
        # Use allocation from manager
        self.capital = manager.total_capital * manager.allocations.get('ai_ensemble', 0.1)
        self.symbols = SYMBOLS
        self.running = False
        # self.ensemble = EnsembleModel() # Replaced by ParallelMLPredictor in main.py
        self.anomaly_detector = AnomalyDetector(threshold=1.5)
        self.risk = RiskManager(state)
        self.mode = os.getenv('AI_ENSEMBLE_MODE', 'long_only')
        self.stability_score = self._load_stability_score()

    def _load_stability_score(self):
        try:
            path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'ml', 'models', 'stability.json')
            if os.path.exists(path):
                with open(path, 'r') as f:
                    data = json.load(f)
                    return data.get('stability_score', 0.5)
        except Exception as e:
            log.error(f"Error loading stability score: {e}")
        return 0.5

    async def run_loop(self):
        self.running = True
        log.info(f"🧠 Start AI ENSEMBLE Loop (Cap: ${self.capital}) Mode: {self.mode}")
        while self.running:
            try:
                for symbol in self.symbols:
                    await self._process(symbol)
            except asyncio.CancelledError:
                break
            except Exception as e:
                log.error(f"AIEnsemble error: {e}")
                log.error(traceback.format_exc())
            await asyncio.sleep(300)  # 5 minutes cycle as requested

    async def _process(self, symbol: str):
        # 1. Gather Data
        df_1h = await self.state.get_df(f"ohlcv:1h:{symbol}", n=100)
        df_1m = await self.state.get_df(f"ohlcv:1m:{symbol}", n=100)
        price = await self.state.get_float(f"price:{symbol}")
        feature_dict = await self.state.get(f"features:{symbol}")
        
        if df_1h is None or len(df_1h) < 20 or not price or not feature_dict:
            return

        # Ensure only numeric data is used for technical calculations
        df_1h = df_1h.select_dtypes(include=[np.number])
        if df_1h.empty: return

        # 2. Anomaly Gating (Paper 1)
        prices_1h = df_1h['close'].tolist()
        anomaly = self.anomaly_detector.detect(prices_1h)
        await self.state.redis.set(f"anomaly:{symbol}", json.dumps(anomaly))
        
        if anomaly['is_abnormal'] and abs(anomaly['z_score']) > 1.5:
            log.warning(f"⚠️ [AI ENSEMBLE] Skipping {symbol} due to Extreme Anomaly (Z={anomaly['z_score']:.2f})")
            return

        # 3. Centralized Model Prediction (from main.py ml_engine_loop)
        prediction = await self.state.get(f"ml_signal:{symbol}")
        if not prediction:
            log.warning(f"⚠️ [AI ENSEMBLE] No fresh ML signal for {symbol}")
            return

        # Score is normalized ensemble value (-1 to 1)
        # Assuming prediction['ensemble_val'] is 0 to 1, shifted to -1 to 1
        score = (prediction['ensemble_val'] - 0.5) * 2
        confidence = prediction.get('confidence', 0.5)

        ml_signal = 0
        if prediction['signal'] == 'BUY': ml_signal = 1
        elif prediction['signal'] == 'SELL': ml_signal = -1

        # 4. Confirmation Indicators (Paper 5)
        # RSI
        rsi_val = float(compute_rsi(df_1h['close'], 14).iloc[-1])
        rsi_sig = 0
        if rsi_val < 30: rsi_sig = 1
        elif rsi_val > 70: rsi_sig = -1
        
        # Ultimate Oscillator (GitHub Repo Integration)
        ultosc_val = float(compute_ultosc(df_1h).iloc[-1])
        ultosc_sig = 0
        if ultosc_val < 30: ultosc_sig = 1
        elif ultosc_val > 70: ultosc_sig = -1
        
        # MACD (using EMA 12, 26, 9)
        ema12 = df_1h['close'].ewm(span=12).mean()
        ema26 = df_1h['close'].ewm(span=26).mean()
        macd_line = ema12 - ema26
        signal_line = macd_line.ewm(span=9).mean()
        
        macd_sig = 0
        if macd_line.iloc[-1] > signal_line.iloc[-1] and macd_line.iloc[-2] <= signal_line.iloc[-2]:
            macd_sig = 1
        elif macd_line.iloc[-1] < signal_line.iloc[-1] and macd_line.iloc[-2] >= signal_line.iloc[-2]:
            macd_sig = -1
            
        # Volume
        vol_sma20 = df_1h['volume'].rolling(20).mean().iloc[-1]
        vol_curr = df_1h['volume'].iloc[-1]
        vol_sig = 0
        if vol_curr > 1.5 * vol_sma20: vol_sig = 1
        elif vol_curr < 0.5 * vol_sma20: vol_sig = -1
        
        # 5. Weighted Score Calculation (Paper 5 Eq 1 + GitHub Algo)
        # score = 0.15*RSI + 0.15*ULTOSC + 0.3*MACD + 0.2*Vol + 0.2*ML
        score = (0.15 * rsi_sig) + (0.15 * ultosc_sig) + (0.3 * macd_sig) + (0.2 * vol_sig) + (0.2 * ml_signal)
        
        log.info(f"📊 [AI ENSEMBLE] {symbol} Score: {score:.2f} (RSI:{rsi_sig} ULTOSC:{ultosc_sig} MACD:{macd_sig} Vol:{vol_sig} ML:{ml_signal})")

        # 4. Indicators (Simplified for signal generation)
        atr = float(compute_atr(df_1h, 14).iloc[-1])
        
        # 5. Custom Technical Filters (The "Custom" Layer)
        ema20 = compute_ema(df_1h['close'], 20).iloc[-1]
        ema50 = compute_ema(df_1h['close'], 50).iloc[-1]
        rsi = compute_rsi(df_1h['close'], 14).iloc[-1]
        
        trend_up = ema20 > ema50
        trend_down = ema20 < ema50
        
        # Volatility Gate: ATR / Price must be > 0.5% (Avoid dead markets)
        volatility_pct = (atr / price) * 100
        if volatility_pct < 0.5:
            log.debug(f"Skipping {symbol}: Low volatility ({volatility_pct:.2f}%)")
            return

        # 6. Trade Logic
        pos = await self.state.get(f"ai_ensemble:pos:{symbol}")

        if pos:
            # Update Trailing Stop
            entry = pos['entry']
            side = pos['side']
            high_low = pos.get('high_low', price)
            
            # Update extreme price
            if side == 'LONG': high_low = max(high_low, price)
            else: high_low = min(high_low, price)
            pos['high_low'] = high_low
            
            # Check Exit
            stop = pos['sl']
            tp = pos['tp']
            
            # Dynamic Trailing SL after 1.5% profit
            pnl_pct = (price - entry) / entry if side == 'LONG' else (entry - price) / entry
            if pnl_pct > 0.015:
                stop = self.risk.check_trailing_stop(side, price, high_low, atr)
                pos['sl'] = stop

            exit_reason = None
            if side == 'LONG':
                if price <= stop: exit_reason = "STOP_LOSS"
                elif price >= tp: exit_reason = "TAKE_PROFIT"
                elif score < -0.4: exit_reason = "SIGNAL_REVERSAL"
            else:
                if price >= stop: exit_reason = "STOP_LOSS"
                elif price <= tp: exit_reason = "TAKE_PROFIT"
                elif score > 0.4: exit_reason = "SIGNAL_REVERSAL"
                
            if exit_reason:
                await self._close_position(symbol, pos, price, exit_reason)
            else:
                # Save updated high_low and SL
                await self.state.set(f"ai_ensemble:pos:{symbol}", pos)
        else:
            if abs(score) > 0.5:
                side = 'LONG' if score > 0.5 else 'SHORT'
                
                # Apply custom filters
                if side == 'LONG':
                    if not trend_up: return # Trend Filter
                    if rsi > 70: return # RSI Overbought Filter
                else:
                    if self.mode == 'long_only': return
                    if not trend_down: return # Trend Filter
                    if rsi < 30: return # RSI Oversold Filter

                # Calculate SL/TP BEFORE entry
                sl = self.risk.get_stop_loss(side, price, atr)
                tp = self.risk.get_take_profit(side, price, atr)
                
                # Compute position size
                size_data = self.risk.compute_position_size(self.capital, abs(score), atr, price)
                qty = size_data['qty']
                
                if qty > 0 and self.risk.validate_trade(side, price, sl, tp, qty, self.capital):
                    # Check MultiStrategyManager for capital/position gating
                    nominal = qty * price
                    if await self.manager.can_open_trade('ai_ensemble', symbol, required_capital=nominal):
                        await self._open_position(symbol, side, price, sl, tp, qty, confidence)

    async def _open_position(self, symbol: str, side: str, price: float, sl: float, tp: float, qty: float, confidence: float):
        pos = {
            'side': side,
            'entry': price,
            'nominal_value': qty * price,
            'sl': sl,
            'tp': tp,
            'high_low': price,
            'qty': qty,
            'time': time.time(),
            'strategy': 'AI_ENSEMBLE',
            'symbol': symbol
        }
        await self.state.set(f"ai_ensemble:pos:{symbol}", pos)
        await self.manager.register_trade('ai_ensemble', pos)
        
        # Signal for dashboard
        signal = {
            'time': time.time(),
            'price': price,
            'type': side,
            'action': 'OPEN',
            'strategy': 'AI_ENSEMBLE'
        }
        await self.state.redis.lpush('signals:history', json.dumps(signal))
        await self.state.redis.ltrim('signals:history', 0, 99)
        
        # Order Request
        req = {'action': 'OPEN', 'side': side, 'qty': qty, 'price': price, 'strategy': 'AI_ENSEMBLE'}
        await self.state.set(f"order_request:{symbol}", req)
        
        log.info(f"🚀 [AI ENSEMBLE] OPEN {side} {symbol} at {price:.2f}")

    async def _close_position(self, symbol: str, pos: dict, price: float, reason: str):
        entry = pos['entry']
        side = pos['side']
        qty = pos['qty']
        
        pnl_usd = (price - entry) * qty if side == 'LONG' else (entry - price) * qty
        await self.pnl.record_trade('AI_ENSEMBLE', symbol, side, entry, price, qty, reason)
        
        await self.state.redis.delete(f"ai_ensemble:pos:{symbol}")
        await self.manager.remove_trade('ai_ensemble', symbol)
        
        # Order Request
        req = {'action': 'CLOSE', 'side': side, 'qty': qty, 'strategy': 'AI_ENSEMBLE'}
        await self.state.set(f"order_request:{symbol}", req)
        
        log.info(f"🛑 [AI ENSEMBLE] CLOSE {side} {symbol} at {price:.2f} PnL: ${pnl_usd:.2f} ({reason})")
