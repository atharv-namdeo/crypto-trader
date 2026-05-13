import sys
import os
import argparse
import pandas as pd
import time
from datetime import datetime
import ccxt

# Add project root to sys.path
sys.path.append(os.getcwd())
from config_symbols import SYMBOL_CONFIG, CryptoTier

def fetch_symbol_data(exchange, symbol, timeframe, days=7, start_date=None, data_dir="backtest_data"):
    """
    Fetch historical data for a symbol (Sync version).
    """
    os.makedirs(data_dir, exist_ok=True)
    filename = f"{data_dir}/{symbol.replace('/', '_')}_{timeframe}.csv"
    
    if start_date:
        since = exchange.parse8601(f"{start_date}T00:00:00Z")
    else:
        since = exchange.milliseconds() - (days * 24 * 60 * 60 * 1000)
    
    end_time = since + (days * 24 * 60 * 60 * 1000)

    print(f"FETCHING {symbol} {timeframe} since {datetime.fromtimestamp(since/1000)}...")
    
    all_ohlcv = []
    current_since = since
    
    while current_since < end_time and current_since < exchange.milliseconds():
        try:
            ohlcv = exchange.fetch_ohlcv(symbol, timeframe, current_since, limit=1000)
            if not ohlcv:
                break
            
            # Filter rows
            valid_rows = [row for row in ohlcv if row[0] <= end_time]
            all_ohlcv.extend(valid_rows)
            
            if len(valid_rows) < len(ohlcv) or not ohlcv:
                break
                
            current_since = ohlcv[-1][0] + 1
            time.sleep(exchange.rateLimit / 1000)
        except Exception as e:
            print(f"ERROR fetching {symbol}: {e}")
            break
            
    if all_ohlcv:
        df = pd.DataFrame(all_ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        df.to_csv(filename, index=False)
        print(f"SAVED {len(df)} rows for {symbol} {timeframe} to {filename}")
    else:
        print(f"WARNING: No data recovered for {symbol}")

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--start", type=str, help="Start date YYYY-MM-DD", default=None)
    parser.add_argument("--days", type=int, help="Number of days", default=7)
    parser.add_argument("--dir", type=str, help="Output directory", default="backtest_data")
    parser.add_argument("--tier", type=str, help="Symbol tier (top/mid/all)", default="top")
    parser.add_argument("--symbols", type=str, help="Comma-separated symbols", default=None)
    parser.add_argument("--timeframes", type=str, help="Comma-separated timeframes", default="1h,1m,1d")
    args = parser.parse_args()

    exchange = ccxt.binance({'enableRateLimit': True})
    
    # Tier mapping
    if args.symbols:
        symbols = args.symbols.split(',')
    elif args.tier == "top":
        symbols = SYMBOL_CONFIG[CryptoTier.TIER_1] + SYMBOL_CONFIG[CryptoTier.TIER_2]
    elif args.tier == "mid":
        symbols = SYMBOL_CONFIG[CryptoTier.TIER_3]
    else:
        symbols = []
        for t in SYMBOL_CONFIG: symbols.extend(SYMBOL_CONFIG[t])
        
    timeframes = args.timeframes.split(',')
    for symbol in symbols:
        for tf in timeframes:
            fetch_symbol_data(exchange, symbol, tf, args.days, args.start, args.dir)
        
    print("SUCCESS: ALL DATA FETCHED")

if __name__ == "__main__":
    main()
