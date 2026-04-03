import sys
import os

# Add project root to sys.path
sys.path.append(os.getcwd())

import ccxt
import pandas as pd
from config_symbols import SYMBOL_CONFIG

DATA_DIR = "backtest_data"
os.makedirs(DATA_DIR, exist_ok=True)

def fetch_all():
    exchange = ccxt.binance()
    symbols = []
    for tier in SYMBOL_CONFIG:
        symbols.extend(SYMBOL_CONFIG[tier])
    
    print(f"🚀 Fetching {len(symbols)} symbols...")
    
    for symbol in symbols:
        for tf in ['1h', '1m']:
            fname = f"{DATA_DIR}/{symbol.replace('/', '_')}_{tf}.csv"
            if os.path.exists(fname): continue
            
            print(f"📥 {symbol} {tf}...", end=" ", flush=True)
            try:
                # 8 days ago
                since = exchange.milliseconds() - (8 * 24 * 3600 * 1000)
                ohlcv = exchange.fetch_ohlcv(symbol, tf, since=since, limit=10000)
                if ohlcv:
                    df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
                    df.to_csv(fname, index=False)
                    print(f"Done ({len(df)} rows)")
                else:
                    print("Empty")
                time.sleep(exchange.rateLimit / 1000)
            except Exception as e:
                print(f"Error: {e}")

if __name__ == "__main__":
    fetch_all()
