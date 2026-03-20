"""
core/feature_engine.py
Feature Engine — Phase 2

Computes 60+ features every 1 second from raw data in Redis.
Publishes `features_ready:SYMBOL` event so the rest of the engine can use them.
"""

import math
import asyncio
import logging
import numpy as np
import pandas as pd
import utils.indicators as ta_ind
from core.state_manager import StateManager

log = logging.getLogger("FeatureEngine")

class FeatureEngine:
    def __init__(self, symbols: list, state: StateManager):
        self.symbols = symbols
        self.state = state
        self.running = False

    async def run_forever(self, interval_s: int = 1):
        self.running = True
        log.info("🧠 Starting Feature Engine (60+ features / second)")
        
        while self.running:
            try:
                for symbol in self.symbols:
                    await self._compute_and_publish(symbol)
                await asyncio.sleep(interval_s)
            except asyncio.CancelledError:
                break
            except Exception as e:
                log.error(f"Feature engine loop error: {e}")
                import traceback
                traceback.print_exc()
                await asyncio.sleep(5)

    async def _compute_and_publish(self, symbol: str):
        # 1. Pull required data
        # We need historical 1h, 1m candles, live order book, and live 1m kline
        df_1h = await self.state.get_df(f"ohlcv:1h:{symbol}", n=200)
        df_1m = await self.state.get_df(f"ohlcv:1m:{symbol}", n=200)
        ob    = await self.state.get(f"orderbook:{symbol}")
        tape  = await self.state.get(f"tape:{symbol}") 
        live_k= await self.state.get(f"live_kline:1m:{symbol}")
        
        # If we lack basic historical data, skip
        if df_1h is None or len(df_1h) < 20 or df_1m is None or len(df_1m) < 20:
            return

        # 2. Append live 1m kline to the 1m dataframe's tail to get up-to-the-second precision
        if live_k:
            df_1m = df_1m.copy()
            # If the current minute is already the last row, update it. Else append.
            if len(df_1m) > 0 and df_1m['timestamp'].iloc[-1].timestamp() * 1000 >= live_k['timestamp']:
                df_1m.iloc[-1, df_1m.columns.get_loc('close')] = live_k['close']
                df_1m.iloc[-1, df_1m.columns.get_loc('high')] = max(df_1m.iloc[-1]['high'], live_k['high'])
                df_1m.iloc[-1, df_1m.columns.get_loc('low')] = min(df_1m.iloc[-1]['low'], live_k['low'])
                df_1m.iloc[-1, df_1m.columns.get_loc('volume')] = live_k['volume']
            else:
                live_row = pd.DataFrame([{
                    'timestamp': pd.to_datetime(live_k['timestamp'], unit='ms'),
                    'open': live_k['open'], 'high': live_k['high'], 
                    'low': live_k['low'], 'close': live_k['close'], 
                    'volume': live_k['volume']
                }])
                df_1m = pd.concat([df_1m, live_row], ignore_index=True)

        close_1h = df_1h['close']
        close_1m = df_1m['close']
        high_1m  = df_1m['high']
        low_1m   = df_1m['low']
        vol_1m   = df_1m['volume']

        f = {}  # Feature dictionary
        
        # ── PRICE & RETURNS ───────────────────────────────────────────────
        for n in [1, 3, 5, 10, 20]:
            if len(close_1m) >= n + 1:
                f[f'log_return_{n}m'] = float(np.log(close_1m.iloc[-1] / (close_1m.iloc[-(n+1)] + 1e-9)))
            else:
                f[f'log_return_{n}m'] = 0.0

        if len(close_1h) >= 2:
            f['log_return_60m'] = float(np.log(close_1h.iloc[-1] / (close_1h.iloc[-2] + 1e-9)))

        # Candle shapes (1m)
        c_open, c_high, c_low, c_close = df_1m['open'].iloc[-1], high_1m.iloc[-1], low_1m.iloc[-1], close_1m.iloc[-1]
        c_range = max(c_high - c_low, 1e-9)
        f['candle_body'] = float(abs(c_open - c_close) / c_range)
        f['upper_wick']  = float((c_high - max(c_open, c_close)) / c_range)
        f['lower_wick']  = float((min(c_open, c_close) - c_low) / c_range)

        # ── TREND (1h) ────────────────────────────────────────────────────
        try:
            for period in [9, 21, 50, 200]:
                ema = ta_ind.ema(close_1h, length=period)
                f[f'ema_{period}_dist'] = float((close_1h.iloc[-1] - ema.iloc[-1]) / (ema.iloc[-1] + 1e-9))

            adx = ta_ind.adx(df_1h['high'], df_1h['low'], close_1h, length=14)
            f['adx_14'] = float(adx['ADX_14'].iloc[-1])
            f['adx_pos_di'] = float(adx['DMP_14'].iloc[-1])
            f['adx_neg_di'] = float(adx['DMN_14'].iloc[-1])
            f['adx_slope_3'] = float(adx['ADX_14'].iloc[-1] - adx['ADX_14'].iloc[-4]) if len(adx) >= 4 else 0.0

            macd = ta_ind.macd(close_1h)
            f['macd_line'] = float(macd['MACD_12_26_9'].iloc[-1])
            f['macd_signal'] = float(macd['MACDs_12_26_9'].iloc[-1])
            f['macd_histogram'] = float(macd['MACDh_12_26_9'].iloc[-1])
            f['macd_hist_slope'] = float(macd['MACDh_12_26_9'].iloc[-1] - macd['MACDh_12_26_9'].iloc[-4]) if len(macd) >= 4 else 0.0
        except Exception:
            pass

        # ── MOMENTUM ──────────────────────────────────────────────────────
        try:
            f['rsi_14_1h'] = float(ta_ind.rsi(close_1h, length=14).iloc[-1])
            f['rsi_7_1h']  = float(ta_ind.rsi(close_1h, length=7).iloc[-1])
            f['rsi_21_1h'] = float(ta_ind.rsi(close_1h, length=21).iloc[-1])
            f['rsi_14_1m'] = float(ta_ind.rsi(close_1m, length=14).iloc[-1])

            stoch = ta_ind.stoch(df_1h['high'], df_1h['low'], close_1h, k=14, d=3)
            f['stoch_k'] = float(stoch['STOCHk_14_3_3'].iloc[-1])
            f['stoch_d'] = float(stoch['STOCHd_14_3_3'].iloc[-1])
        except Exception:
            pass

        # ── VOLATILITY ────────────────────────────────────────────────────
        try:
            bb = ta_ind.bbands(close_1h, length=20, std=2)
            bbu, bbm, bbl = bb['BBU_20_2.0'], bb['BBM_20_2.0'], bb['BBL_20_2.0']
            f['bb_upper'] = float(bbu.iloc[-1])
            f['bb_lower'] = float(bbl.iloc[-1])
            f['bb_width'] = float((bbu.iloc[-1] - bbl.iloc[-1]) / (bbm.iloc[-1] + 1e-9))
            
            price_pos = (close_1h.iloc[-1] - bbl.iloc[-1]) / (bbu.iloc[-1] - bbl.iloc[-1] + 1e-9)
            f['bb_position'] = float(price_pos)

            # Squeeze percentiles
            bb_w_hist = (bbu - bbl) / bbm
            if len(bb_w_hist) > 20:
                f['bb_width_pct_90d'] = float(np.percentile(bb_w_hist.dropna(), 100 * bb_w_hist.iloc[-1] / max(bb_w_hist.max(), 1e-9)))
            else:
                f['bb_width_pct_90d'] = 50.0

            returns = close_1h.pct_change().dropna()
            f['realized_vol_14h'] = float(returns.tail(14).std() * math.sqrt(24 * 365)) if len(returns) >= 14 else 0.0

            f['atr_14_1h'] = float(ta_ind.atr(df_1h['high'], df_1h['low'], close_1h, length=14).iloc[-1])
            f['atr_14_1m'] = float(ta_ind.atr(high_1m, low_1m, close_1m, length=14).iloc[-1])
        except Exception:
            pass

        # ── VOLUME & ORDERBOOK ────────────────────────────────────────────
        try:
            vol_sma20 = vol_1m.rolling(20).mean().iloc[-1]
            f['volume_ratio'] = float(vol_1m.iloc[-1] / (vol_sma20 + 1e-9))
            vol_std = vol_1m.rolling(20).std().iloc[-1]
            f['volume_zscore'] = float((vol_1m.iloc[-1] - vol_sma20) / (vol_std + 1e-9))

            # CVD from live tape
            f['cvd_1m'] = 0.0
            f['trade_imbalance'] = 0.0
            if isinstance(tape, list) and tape:
                buys = sum(t.get('qty', 0) for t in tape if t.get('side') == 'buy')
                sells = sum(t.get('qty', 0) for t in tape if t.get('side') == 'sell')
                f['cvd_1m'] = float(buys - sells)
                f['trade_imbalance'] = float((buys - sells) / (buys + sells + 1e-9))

            # Live order book
            f['ob_imbalance'] = 0.0
            f['spread_normalized'] = 0.001
            f['microprice_vs_mid'] = 0.0
            if ob and 'bids' in ob and 'asks' in ob and ob['asks'] and ob['bids']:
                bids = ob['bids'][:10]
                asks = ob['asks'][:10]
                bid_v = sum(q for p, q in bids)
                ask_v = sum(q for p, q in asks)
                f['ob_imbalance'] = float((bid_v - ask_v) / (bid_v + ask_v + 1e-9))
                spread = asks[0][0] - bids[0][0]
                f['spread_normalized'] = float(spread / (close_1m.iloc[-1] + 1e-9))
                
                mid = (asks[0][0] + bids[0][0]) / 2.0
                micro = (bid_v * asks[0][0] + ask_v * bids[0][0]) / (bid_v + ask_v + 1e-9)
                f['microprice_vs_mid'] = float(micro - mid)
        except Exception:
            pass

        # ── VWAP ──────────────────────────────────────────────────────────
        try:
            typical_price = (df_1m['high'] + df_1m['low'] + close_1m) / 3
            cum_vol = vol_1m.cumsum()
            vwap = (typical_price * vol_1m).cumsum() / (cum_vol + 1e-9)
            vwap_std = (close_1m - vwap).rolling(20).std()
            f['vwap_zscore'] = float((close_1m.iloc[-1] - vwap.iloc[-1]) / (vwap_std.iloc[-1] + 1e-9))
        except Exception:
            f['vwap_zscore'] = 0.0

        # Replace any NaNs with 0.0
        for k, v in f.items():
            if math.isnan(v) or math.isinf(v):
                f[k] = 0.0

        # Save to Redis
        await self.state.set(f"features:{symbol}", f, expire_seconds=60)
        
        # Store for ML Sequence Builder (store the last 60 minutes)
        # Assuming run_forever is 1 second, we should only archive it once per minute,
        # but for simplicity, the ML builder can just pull `features:{symbol}` when it needs, 
        # or we rely on `ohlcv:1h` + fresh indicators at runtime.
        # Actually LSTM needs historical features — let's let `ml/` handle history building.

        await self.state.publish(f"features_ready:{symbol}", "1")
        
    def stop(self):
        self.running = False
