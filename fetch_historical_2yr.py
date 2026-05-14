import ccxt
import pandas as pd
import time
import os
from datetime import datetime, timedelta

def fetch_2yr_data(symbol, timeframe='1h'):
    exchange = ccxt.binance()
    since = exchange.parse8601((datetime.now() - timedelta(days=730)).isoformat())
    
    all_ohlcv = []
    while since < exchange.milliseconds():
        try:
            print(f"Fetching {symbol} from {exchange.iso8601(since)}...")
            ohlcv = exchange.fetch_ohlcv(symbol, timeframe, since, limit=1000)
            if not ohlcv:
                break
            all_ohlcv.extend(ohlcv)
            since = ohlcv[-1][0] + 1
            time.sleep(exchange.rateLimit / 1000)
        except Exception as e:
            print(f"Error fetching {symbol}: {e}")
            time.sleep(5)
            
    df = pd.DataFrame(all_ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
    df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
    
    os.makedirs('data/historical_2yr', exist_ok=True)
    filename = f"data/historical_2yr/{symbol.replace('/', '_')}_{timeframe}.csv"
    df.to_csv(filename, index=False)
    print(f"Saved {len(df)} bars to {filename}")

if __name__ == "__main__":
    symbols = ["BTC/USDT", "ETH/USDT", "SOL/USDT", "XRP/USDT", "ADA/USDT", "DOGE/USDT", "SHIB/USDT", "AVAX/USDT", "LINK/USDT"]
    for s in symbols:
        fetch_2yr_data(s)
