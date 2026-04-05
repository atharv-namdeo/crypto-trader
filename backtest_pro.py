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
from core.advanced_risk_engine import AdvancedRiskEngine
from core.strategy_selector import StrategySelector

# Constants
FEE_RATE = 0.0004  # 0.04% Taker Fee
INITIAL_CAPITAL_USD = 1204.0
DATA_DIR = "backtest_data_oct2025"

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
log = logging.getLogger("BacktestExpert")

class ExpertBacktestEngine:
    def __init__(self, symbols, initial_capital, live_mode=False, data_dir=None):
        self.symbols = symbols
        self.capital = initial_capital
        self.initial_capital = initial_capital
        self.data_dir = data_dir or DATA_DIR
        self.positions = {}
        self.trades = []
        self.slippage_model = SlippageModel()
        self.live_mode = live_mode
        self.exchange = ccxt.binance() if ccxt else None
        self.btc_h = None
        
        # Autonomous Components (Simulated)
        # Note: We pass None for StateManager in backtest to avoid Redis side-effects
        self.risk_engine = AdvancedRiskEngine(None) 
        self.strategy_selector = StrategySelector(None)
        
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
            f1h = os.path.join(self.data_dir, "BTC_USDT_1h.csv")
            if os.path.exists(f1h):
                self.btc_h = pd.read_csv(f1h)
        
        if self.btc_h is not None:
            self.btc_h['ts'] = pd.to_datetime(self.btc_h['timestamp'], unit='ms')
            self.btc_h['adx'] = compute_adx_df(self.btc_h)
            self.btc_h['atr'] = compute_atr(self.btc_h)
            self.btc_h['rsi'] = compute_rsi(self.btc_h['close'])
            self.btc_h['ema20'] = compute_ema(self.btc_h['close'], 20)
            self.btc_h['ema50'] = compute_ema(self.btc_h['close'], 50)
            sma20 = self.btc_h['close'].rolling(20).mean()
            std20 = self.btc_h['close'].rolling(20).std()
            self.btc_h['bbw'] = (4 * std20) / (sma20 + 1e-9)

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
        
        f1h = os.path.join(self.data_dir, f"{symbol.replace('/', '_')}_1h.csv")
        f1m = os.path.join(self.data_dir, f"{symbol.replace('/', '_')}_1m.csv")
        if not os.path.exists(f1h) or not os.path.exists(f1m): return None, None
        return pd.read_csv(f1h), pd.read_csv(f1m)

    def detect_regime(self, btc_row):
        """10-Phase Market Cycle Detection (Synchronized with core)"""
        if btc_row is None or btc_row.empty: return "UNKNOWN"
        
        adx = btc_row['adx']
        rsi = btc_row['rsi']
        ema20 = btc_row['ema20']
        ema50 = btc_row['ema50']
        bbw = btc_row['bbw']
        is_uptrend = ema20 > ema50
        
        if is_uptrend:
            if adx > 20 and rsi > 52: # Calibrated for January Alpha capture
                return "EARLY_BULL_BREAKOUT" if adx < 35 else "MATURE_BULL_EXTENSION"
            if rsi < 48: return "BULL_CORRECTION"
        else:
            if adx > 20 and rsi < 48:
                return "EARLY_BEAR_BREAKDOWN" if adx < 35 else "MATURE_BEAR_DECLINE"
            if rsi > 52: return "BEAR_BOUNCE"
            
        if bbw < 0.015: return "ACCUMULATION"
        if bbw > 0.04: return "CONSOLIDATION_WIDE"
        return "CONSOLIDATION_NARROW"

    def compute_strategy_score(self, h_row, btc_row, m_row=None):
        # 1. Indicator Votes
        rsi_sig = 1 if h_row['rsi'] < 30 else (-1 if h_row['rsi'] > 70 else 0)
        ult_sig = 1 if h_row['ultosc'] < 30 else (-1 if h_row['ultosc'] > 70 else 0)
        macd_sig = 1 if h_row['macd'] > h_row['macd_s'] else -1
        
        # 2. MTF Quorum Check (Simulated)
        # We check if 1h trend matches our signal
        ema_match = 1 if h_row['ema20'] > h_row['ema50'] else -1
        
        votes = [rsi_sig, ult_sig, macd_sig, ema_match]
        buy_votes = sum(1 for v in votes if v == 1)
        sell_votes = sum(1 for v in votes if v == -1)
        
        quorum = buy_votes >= 2 or sell_votes >= 2
        
        # 3. Final Ensemble Score
        base = (0.15 * rsi_sig) + (0.15 * ult_sig) + (0.5 * macd_sig) + (0.2 * ema_match)
        return base, max(buy_votes, sell_votes)

    def run_backtest(self, symbol):
        df_h, df_m = self.load_data(symbol)
        if df_h is None or self.btc_h is None: return
        df_h['rsi'] = compute_rsi(df_h['close']); df_h['ultosc'] = compute_ultosc(df_h)
        df_h['atr'] = compute_atr(df_h)
        df_h['atr_short'] = compute_atr(df_h, 5)
        df_h['atr_long'] = compute_atr(df_h, 30)
        df_h['ema20'] = compute_ema(df_h['close'], 20)
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
                    self.trades.append({
                        'symbol': symbol, 'side': pos['side'], 'pnl_net': pnl_n, 
                        'reason': reason, 'time': curr_ts, 'regime': regime, 
                        'strategy': pos.get('strategy', 'unknown')
                    })
                    del self.positions[symbol]; continue

            # 1. Strategy & Risk Gating
            # 1. Market Regime & Quorum (Nuclear Hardening v10.0)
            regime = self.detect_regime(btc_row)
            
            # Institutional Gating Dictionary
            regime_mults = {
                'TRENDING_BULL': 1.5,
                'TRENDING_BEAR': 1.2,
                'MATURE_BULL_EXTENSION': 1.0,
                'MATURE_BEAR_DECLINE': 1.0,
                'EARLY_BULL_BREAKOUT': 0.8,
                'EARLY_BEAR_BREAKDOWN': 0.8,
                'BULL_CORRECTION': 0.0,    # NUCLEAR GATE ✅
                'BEAR_BOUNCE': 0.0,        # NUCLEAR GATE ✅
                'CONSOLIDATION_WIDE': 0.0, # NUCLEAR GATE ✅
                'CONSOLIDATION_NARROW': 0.0,# NUCLEAR GATE ✅
                'ACCUMULATION': 0.0,        # NUCLEAR GATE ✅
                'HIGH_VOL_CHOP': 0.1       # DEFENSIVE ✅
            }
            
            # ABSOLUTE GATE CHECK
            mult = regime_mults.get(regime, 0.0) # Default to 0.0 for safety
            if mult <= 0.0:
                continue

            score, votes_agreement = self.compute_strategy_score(h_row, btc_row)
            required_v = self.strategy_selector.get_required_quorum(regime)
            
            # 2. Portfolio Lockdown (Anti-Liquidation)
            current_pnl_pct = (self.capital - self.initial_capital) / self.initial_capital * 100
            lockdown_mult = self.risk_engine.get_lockdown_multiplier(current_pnl_pct)
            
            # 2a. Global Volatility Gate (Institutional Predator v8.0)
            atr_short = h_row['atr_short']
            atr_long = h_row['atr_long']
            vol_coeff = atr_short / (atr_long + 1e-9) if atr_long > 0 else 1.0
            
            vol_tighten = 1.0
            if vol_coeff > 1.8: vol_tighten = 0.5  # Adaptive Stop-Loss Tightening
            
            mult *= lockdown_mult
            if len(self.positions) >= self.risk_engine.max_simultaneous_trades:
                continue

            # 4. Signal Validation
            required_conf = 0.50 
            required_v = self.strategy_selector.get_required_quorum(regime)
            
            if "CONSOLIDATION" in regime: required_conf = 0.85 # Harder to enter in chop
            if "BREAKOUT" in regime: required_conf = 0.85      # Quality filter for breakouts
            
            if abs(score) >= required_conf and votes_agreement >= required_v and symbol not in self.positions:
                side = 'LONG' if score > 0 else 'SHORT'
                if side == 'SHORT' and regime == 'TRENDING_BULL': continue
                
                # 1. Strategy Selection (Autonomous Phase 1)
                strategy = self.strategy_selector.regime_map.get(regime)
                if not strategy:
                    if _ % 100 == 0: log.debug(f"Block: {symbol} in {regime}")
                    continue
                
                # 2. Advanced Risk Engine (Predator Adaptive Stops v8.0)
                m = self.risk_engine.stop_multipliers.get(regime, {'sl': 3.0, 'tp': 6.0})
                atr = h_row['atr'] if h_row['atr'] > 0 else price * 0.01
                
                # Apply volatility tightening to SL
                sl = price - (atr * m['sl'] * vol_tighten) if side == 'LONG' else price + (atr * m['sl'] * vol_tighten)
                tp = price + (atr * m['tp']) if side == 'LONG' else price - (atr * m['tp'])
                
                # Kelly Sizing Simulation
                # Use mult as a performance bias
                risk_pct = 0.02 * mult # 2% Base Risk * Regime Mult
                risk_amt = self.capital * risk_pct
                qty = risk_amt / (abs(price - sl) + 1e-9)
                
                slip = self.slippage_model.estimate_slippage(symbol, tier, qty, price)
                real_en = price * (1 + slip) if side == 'LONG' else price * (1 - slip)
                self.positions[symbol] = {
                    'side': side, 'entry_raw': price, 'entry_fee': (qty*price*FEE_RATE), 
                    'qty': qty, 'sl': sl, 'tp': tp, 'regime': regime, 'strategy': strategy
                }
                log.info(f"✅ [ENTRY] {symbol} {side} ({strategy}) Score:{score:.2f} Reg:{regime}")

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
            
        report += "\n## Portfolio Attribution by Strategy\n"
        if 'strategy' in df.columns:
            for strat, group in df.groupby('strategy'):
                win_rate = len(group[group['pnl_net']>0])/len(group)*100
                report += f"- **{strat.upper()}**: ${group['pnl_net'].sum():+.2f} | Win Rate: {win_rate:.1f}% | {len(group)} trades\n"
        
        report += "\n## Recent Trades\n" + df.tail(15)[['time', 'symbol', 'side', 'strategy', 'pnl_net', 'reason', 'regime']].to_markdown()
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
    parser.add_argument("--dir", type=str, help="Override data directory", default=None)
    parser.add_argument("--output", type=str, help="Override report filename", default=None)
    args = parser.parse_args()
    
    all_symbols = []
    for t in SYMBOL_CONFIG: all_symbols.extend(SYMBOL_CONFIG[t])
    
    engine = ExpertBacktestEngine(all_symbols, INITIAL_CAPITAL_USD, live_mode=args.live, data_dir=args.dir)
    for s in all_symbols:
        try: engine.run_backtest(s)
        except Exception as e: log.error(f"Error {s}: {e}")
            
    report = engine.generate_report()
    print(report)
    
    if args.output:
        fname = args.output
    else:
        fname = "backtest_hybrid_live_report.md" if args.live else "backtest_hybrid_csv_report.md"
        
    with open(fname, "w") as f: f.write(report)
    log.info(f"Expert Phase 7 Completed. Report saved to {fname}")
