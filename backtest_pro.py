import sys
import os
import pandas as pd
import numpy as np
import logging
import json
import argparse
from datetime import datetime
try:
    import ccxt
except ImportError:
    ccxt = None

# Add project root to sys.path
sys.path.append(os.getcwd())

from config_symbols import SYMBOL_CONFIG
from core.utils import compute_rsi, compute_atr, compute_ultosc, compute_ema
from execution.slippage_model import SlippageModel

# Constants
FEE_RATE = 0.0004  # 0.04% Taker Fee
INITIAL_CAPITAL_USD = 1204.0
DATA_DIR = "backtest_data"

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
log = logging.getLogger("BacktestExpert")

class ExpertBacktestEngine:
    def __init__(self, symbols, initial_capital, live_mode=False):
        self.symbols = symbols
        self.capital = initial_capital
        self.initial_capital = initial_capital
        self.positions = {}
        self.trades = []
        self.slippage_model = SlippageModel()
        self.live_mode = live_mode
        self.exchange = ccxt.binance() if ccxt else None
        self.btc_h = None
        self._load_btc_data()

    def _load_btc_data(self):
        if self.live_mode and self.exchange:
            log.info("🌐 Fetching Live BTC Data for Regime Detection...")
            try:
                ohlcv = self.exchange.fetch_ohlcv('BTC/USDT', '1h', limit=168)
                self.btc_h = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
            except Exception as e:
                log.error(f"Failed to fetch live BTC data: {e}")
                self.live_mode = False # Fallback
        
        if not self.live_mode:
            f1h = os.path.join(DATA_DIR, "BTC_USDT_1h.csv")
            if os.path.exists(f1h):
                self.btc_h = pd.read_csv(f1h)
        
        if self.btc_h is not None:
            self.btc_h['ts'] = pd.to_datetime(self.btc_h['timestamp'], unit='ms')
            self.btc_h['adx'] = compute_adx_df(self.btc_h)
            self.btc_h['atr'] = compute_atr(self.btc_h)
            self.btc_h['rsi'] = compute_rsi(self.btc_h['close'])

    def load_data(self, symbol):
        if self.live_mode and self.exchange:
            log.info(f"🌐 Fetching Live Data for {symbol}...")
            try:
                h1 = self.exchange.fetch_ohlcv(symbol, '1h', limit=168)
                m1 = self.exchange.fetch_ohlcv(symbol, '1m', limit=1440)
                df_h = pd.DataFrame(h1, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
                df_m = pd.DataFrame(m1, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
                return df_h, df_m
            except: return None, None
        
        f1h = os.path.join(DATA_DIR, f"{symbol.replace('/', '_')}_1h.csv")
        f1m = os.path.join(DATA_DIR, f"{symbol.replace('/', '_')}_1m.csv")
        if not os.path.exists(f1h) or not os.path.exists(f1m): return None, None
        return pd.read_csv(f1h), pd.read_csv(f1m)

    def detect_regime(self, btc_row):
        if btc_row is None or btc_row.empty: return "NEUTRAL"
        adx, rsi = btc_row['adx'], btc_row['rsi']
        atr_pct = (btc_row['atr'] / btc_row['close']) * 100
        if adx > 25:
            return "TRENDING_BULL" if rsi > 55 else ("TRENDING_BEAR" if rsi < 45 else "TRENDING_NEUTRAL")
        return "HIGH_VOL_CHOP" if atr_pct > 0.8 else "LOW_VOL_ACCUMULATION"

    def compute_strategy_score(self, h_row, btc_row):
        rsi_sig = 1 if h_row['rsi'] < 30 else (-1 if h_row['rsi'] > 70 else 0)
        ult_sig = 1 if h_row['ultosc'] < 30 else (-1 if h_row['ultosc'] > 70 else 0)
        macd_sig = 1 if h_row['macd'] > h_row['macd_s'] else -1
        score = (0.2 * rsi_sig) + (0.2 * ult_sig) + (0.4 * macd_sig)
        if h_row['volume'] > h_row['vol_sma'] and h_row['close'] > h_row['ema20']: score += 0.2
        return score

    def run_backtest(self, symbol):
        df_h, df_m = self.load_data(symbol)
        if df_h is None or self.btc_h is None: return
        df_h['rsi'] = compute_rsi(df_h['close']); df_h['ultosc'] = compute_ultosc(df_h)
        df_h['atr'] = compute_atr(df_h); df_h['ema20'] = compute_ema(df_h['close'], 20)
        df_h['ema50'] = compute_ema(df_h['close'], 50)
        ema12 = compute_ema(df_h['close'], 12); ema26 = compute_ema(df_h['close'], 26)
        df_h['macd'] = ema12 - ema26; df_h['macd_s'] = compute_ema(df_h['macd'], 9)
        df_h['vol_sma'] = df_h['volume'].rolling(20).mean()
        df_h['ts'] = pd.to_datetime(df_h['timestamp'], unit='ms')
        df_m['ts'] = pd.to_datetime(df_m['timestamp'], unit='ms')
        
        sim_df = df_m.iloc[::5]
        if not self.live_mode: sim_df = sim_df.tail(2000)
        
        tier = self.slippage_model.get_tier(symbol)
        
        for _, m_row in sim_df.iterrows():
            curr_ts = m_row['ts']
            h_slice = df_h[df_h['ts'] <= curr_ts]
            btc_slice = self.btc_h[self.btc_h['ts'] <= curr_ts]
            if h_slice.empty or btc_slice.empty: continue
            h_row, btc_row = h_slice.iloc[-1], btc_slice.iloc[-1]
            regime = self.detect_regime(btc_row)
            price = m_row['close']
            
            if symbol in self.positions:
                pos = self.positions[symbol]
                exit_p = None; reason = None
                if pos['side'] == 'LONG':
                    if m_row['low'] <= pos['sl']: exit_p, reason = pos['sl'], "STOP_LOSS"
                    elif m_row['high'] >= pos['tp']: exit_p, reason = pos['tp'], "TAKE_PROFIT"
                else:
                    if m_row['high'] >= pos['sl']: exit_p, reason = pos['sl'], "STOP_LOSS"
                    elif m_row['low'] <= pos['tp']: exit_p, reason = pos['tp'], "TAKE_PROFIT"
                
                if exit_p:
                    slip = self.slippage_model.estimate_slippage(symbol, tier, pos['qty'], exit_p)
                    real_ex = exit_p * (1 - slip) if pos['side'] == 'LONG' else exit_p * (1 + slip)
                    pnl_g = (real_ex - pos['entry_raw']) * pos['qty'] if pos['side'] == 'LONG' else (pos['entry_raw'] - real_ex) * pos['qty']
                    pnl_n = pnl_g - (pos['entry_fee'] + (real_ex * pos['qty'] * FEE_RATE))
                    self.capital += pnl_n
                    self.trades.append({'symbol': symbol, 'side': pos['side'], 'pnl_net': pnl_n, 'reason': reason, 'time': curr_ts, 'regime': regime})
                    del self.positions[symbol]; continue

            score = self.compute_strategy_score(h_row, btc_row)
            regime_mults = {'TRENDING_BULL': 1.5, 'TRENDING_BEAR': 1.2, 'HIGH_VOL_CHOP': 0.1, 'LOW_VOL_ACCUMULATION': 0.4}
            mult = regime_mults.get(regime, 1.0)
            
            if abs(score) >= 0.35 and symbol not in self.positions:
                side = 'LONG' if score > 0 else 'SHORT'
                if side == 'SHORT' and regime == 'TRENDING_BULL': continue
                if (side == 'LONG' and h_row['ema20'] < h_row['ema50']) or (side == 'SHORT' and h_row['ema20'] > h_row['ema50']): continue
                
                atr = h_row['atr'] if h_row['atr'] > 0 else price * 0.01
                sl = price - (atr * 2.5) if side == 'LONG' else price + (atr * 2.5)
                tp = price + (atr * 5.5) if side == 'LONG' else price - (atr * 5.5)
                
                risk_amt = self.capital * 0.005 * mult
                qty = risk_amt / (abs(price - sl) + 1e-9)
                slip = self.slippage_model.estimate_slippage(symbol, tier, qty, price)
                real_en = price * (1 + slip) if side == 'LONG' else price * (1 - slip)
                self.positions[symbol] = {'side': side, 'entry_raw': price, 'entry_fee': (qty*price*FEE_RATE), 'qty': qty, 'sl': sl, 'tp': tp, 'regime': regime}
                log.info(f"✅ [ENTRY] {symbol} {side} Score:{score:.2f} Reg:{regime} Mult:{mult:.1f}")

    def generate_report(self):
        if not self.trades: return "# Backtest Report\nNo trades."
        df = pd.DataFrame(self.trades)
        total_pnl = df['pnl_net'].sum()
        report = f"# Expert Phase 7 Hybrid Backtest Report ({'LIVE' if self.live_mode else 'CSV'})\n"
        report += f"- Initial: ${self.initial_capital:.2f} | Final: ${self.capital:.2f} | PnL: ${total_pnl:.2f} ({total_pnl/self.initial_capital*100:+.2f}%)\n"
        report += f"- Win Rate: {len(df[df['pnl_net']>0])/len(df)*100:.1f}% | Total Trades: {len(df)}\n"
        report += f"- Profit Factor: {abs(df[df['pnl_net']>0]['pnl_net'].sum() / (df[df['pnl_net']<0]['pnl_net'].sum() if not df[df['pnl_net']<0].empty else -1e-9)):.2f}\n\n"
        report += "## Performance by Regime\n"
        for reg, group in df.groupby('regime'):
            report += f"- **{reg}**: ${group['pnl_net'].sum():+.2f} ({len(group)} trades)\n"
        report += "\n## Recent Trades\n" + df.tail(15)[['time', 'symbol', 'side', 'pnl_net', 'reason', 'regime']].to_markdown()
        return report

def compute_adx_df(df, window=14):
    up, down = df['high'].diff(), -df['low'].diff()
    plus_dm = np.where((up > down) & (up > 0), up, 0)
    minus_dm = np.where((down > up) & (down > 0), down, 0)
    tr = pd.concat([df['high'] - df['low'], (df['high'] - df['close'].shift()).abs(), (df['low'] - df['close'].shift()).abs()], axis=1).max(axis=1)
    atr = tr.rolling(window).mean()
    plus_di = 100 * (pd.Series(plus_dm).rolling(window).mean() / (atr + 1e-9))
    minus_di = 100 * (pd.Series(minus_dm).rolling(window).mean() / (atr + 1e-9))
    dx = 100 * (plus_di - minus_di).abs() / (plus_di + minus_di + 1e-9)
    return dx.rolling(window).mean()

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--live", action="store_true", help="Fetch live data from Binance")
    args = parser.parse_args()
    
    all_symbols = []
    for t in SYMBOL_CONFIG: all_symbols.extend(SYMBOL_CONFIG[t])
    
    engine = ExpertBacktestEngine(all_symbols, INITIAL_CAPITAL_USD, live_mode=args.live)
    for s in all_symbols:
        try: engine.run_backtest(s)
        except Exception as e: log.error(f"Error {s}: {e}")
            
    report = engine.generate_report()
    print(report)
    fname = "backtest_hybrid_live_report.md" if args.live else "backtest_hybrid_csv_report.md"
    with open(fname, "w") as f: f.write(report)
    log.info(f"Expert Phase 7 Completed. Report saved to {fname}")
