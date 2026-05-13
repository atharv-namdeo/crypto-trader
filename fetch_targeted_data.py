import ccxt
import pandas as pd
import os
import time
import argparse
from datetime import datetime

def fetch_ohlcv(exchange, symbol, timeframe, start_date, end_date):
    since = exchange.parse8601(f"{start_date}T00:00:00Z")
    end_ms = exchange.parse8601(f"{end_date}T23:59:59Z")
    
    # Add warmup period (300 days for 1d, 60 days for 1h)
    if timeframe == '1d':
        since -= 300 * 24 * 3600 * 1000
    elif timeframe == '1h':
        since -= 60 * 24 * 3600 * 1000
        
    all_ohlcv = []
    while since < end_ms:
        try:
            ohlcv = exchange.fetch_ohlcv(symbol, timeframe, since, limit=1000)
            if not ohlcv: break
            all_ohlcv.extend(ohlcv)
            since = ohlcv[-1][0] + 1
            if len(ohlcv) < 1000: break # reached the end
            time.sleep(exchange.rateLimit / 1000.0)
        except Exception as e:
            print(f"Error fetching {symbol} {timeframe}: {e}")
            time.sleep(1)
            
    if all_ohlcv:
        df = pd.DataFrame(all_ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        # Filter to make sure we don't return data past end_date (except for 1m where we don't have warmup)
        return df
    return None

def main():
    parser = argparse.ArgumentParser(description='Fetch targeted OHLCV data for backtesting')
    parser.add_argument('--start', required=True, help='Start date (YYYY-MM-DD)')
    parser.add_argument('--end', required=True, help='End date (YYYY-MM-DD)')
    parser.add_argument('--output', required=True, help='Output directory')
    args = parser.parse_args()

    exchange = ccxt.binance({'enableRateLimit': True})
    symbols = ['BTC/USDT', 'ETH/USDT', 'SOL/USDT', 'XRP/USDT', 'ADA/USDT', 'DOGE/USDT', 'SHIB/USDT', 'POL/USDT', 'AVAX/USDT', 'LINK/USDT']
    
    os.makedirs(args.output, exist_ok=True)
    
    for s in symbols:
        print(f"Fetching {s} for period {args.start} to {args.end}...")
        
        # 1d with 300 days warmup
        df_1d = fetch_ohlcv(exchange, s, '1d', args.start, args.end)
        if df_1d is not None: df_1d.to_csv(f"{args.output}/{s.replace('/', '_')}_1d.csv", index=False)
        
        # 1h with 60 days warmup
        df_1h = fetch_ohlcv(exchange, s, '1h', args.start, args.end)
        if df_1h is not None: df_1h.to_csv(f"{args.output}/{s.replace('/', '_')}_1h.csv", index=False)
        
        # 1m (no warmup needed for simulation window)
        df_1m = fetch_ohlcv(exchange, s, '1m', args.start, args.end)
        if df_1m is not None: df_1m.to_csv(f"{args.output}/{s.replace('/', '_')}_1m.csv", index=False)

if __name__ == "__main__":
    main()
