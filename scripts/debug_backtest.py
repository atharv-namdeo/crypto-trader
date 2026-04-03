import sys
import os
import pandas as pd
import numpy as np
import logging

# Add project root to sys.path
sys.path.append(os.getcwd())
from config_symbols import SYMBOL_CONFIG

def rsi(series, n=14):
    delta = series.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=n).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=n).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))

def ema(series, n):
    return series.ewm(span=n, adjust=False).mean()

DATA_DIR = "backtest_data"

def run_debug():
    symbol = "BTC/USDT"
    f1h = f"{DATA_DIR}/{symbol.replace('/', '_')}_1h.csv"
    f1m = f"{DATA_DIR}/{symbol.replace('/', '_')}_1m.csv"
    
    if not os.path.exists(f1h):
        print(f"File {f1h} missing!")
        return

    df1h = pd.read_csv(f1h); df1h['timestamp'] = pd.to_datetime(df1h['timestamp'], unit='ms')
    df1m = pd.read_csv(f1m); df1m['timestamp'] = pd.to_datetime(df1m['timestamp'], unit='ms')
    
    df1h['rsi'] = rsi(df1h['close'])
    df1h['ema9'] = ema(df1h['close'], 9)
    df1h['ema21'] = ema(df1h['close'], 21)
    
    sim_df = df1m.iloc[::5].tail(100)
    print(f"Simulating {len(sim_df)} steps...")
    
    trades = []
    capital = 1204.0
    pos = None
    
    for i, row in sim_df.iterrows():
        curr_time, price = row['timestamp'], row['close']
        h_rows = df1h[df1h['timestamp'] <= curr_time]
        if h_rows.empty: continue
        h_row = h_rows.iloc[-1]
        
        if pos:
            # Simple check
            pnl = (price - pos['entry']) * pos['qty'] if pos['side'] == 'LONG' else (pos['entry'] - price) * pos['qty']
            if abs(pnl/pos['entry']) > 0.01: # 1% move
                capital += pnl
                trades.append(pnl)
                pos = None
            continue

        # Signal: EMA Cross
        if h_row['ema9'] > h_row['ema21']:
            side = 'LONG'
        else:
            side = 'SHORT'
            
        pos = {'side': side, 'entry': price, 'qty': (capital * 0.1)/price}
        if i < sim_df.index[5]: # Debug first 5
            print(f"Step {i}: Price={price:.2f} EMA9={h_row['ema9']:.2f} EMA21={h_row['ema21']:.2f} Signal={side}")

    print(f"Done. Trades: {len(trades)}")

if __name__ == "__main__":
    run_debug()
