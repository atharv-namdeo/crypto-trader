import sys
import os

# Add project root to sys.path
sys.path.append(os.getcwd())

import asyncio
import pandas as pd
import time
from datetime import datetime, timedelta
from config_symbols import SYMBOL_CONFIG
import ccxt.async_support as ccxt

# Setup Data Directory
DATA_DIR = "backtest_data"
os.makedirs(DATA_DIR, exist_ok=True)

async def fetch_symbol_data(exchange, symbol, timeframe, days=8):
    """Fetch 'days' of data for a symbol/timeframe and save to CSV."""
    filename = f"{DATA_DIR}/{symbol.replace('/', '_')}_{timeframe}.csv"
    
    # Skip if already exists and is fresh (less than 1 day old)
    if os.path.exists(filename):
        mtime = os.path.getmtime(filename)
        if time.time() - mtime < 86400:
            print(f"✅ {symbol} {timeframe} already exists. Skipping.")
            return

    print(f"📥 Fetching {symbol} {timeframe}...")
    since = exchange.milliseconds() - (days * 24 * 60 * 60 * 1000)
    
    all_ohlcv = []
    while since < exchange.milliseconds():
        try:
            ohlcv = await exchange.fetch_ohlcv(symbol, timeframe, since, limit=1000)
            print(f"DEBUG: {symbol} {timeframe} fetched {len(ohlcv)} rows")
            if not ohlcv:
                break
            all_ohlcv.extend(ohlcv)
            since = ohlcv[-1][0] + 1
            await asyncio.sleep(exchange.rateLimit / 1000)
        except Exception as e:
            print(f"❌ Error fetching {symbol}: {e}")
            break
            
    if all_ohlcv:
        df = pd.DataFrame(all_ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        df.to_csv(filename, index=False)
        print(f"💾 Saved {len(df)} rows for {symbol} {timeframe}")

async def main():
    exchange = ccxt.binance({'enableRateLimit': True})
    
    symbols = []
    for tier in SYMBOL_CONFIG:
        symbols.extend(SYMBOL_CONFIG[tier])
        
    print(f"🚀 Starting data fetch for {len(symbols)} symbols...")
    
    tasks = []
    for symbol in symbols:
        # Fetch both 1h and 1m as required by AIEnsembleStrategy
        tasks.append(fetch_symbol_data(exchange, symbol, '1h'))
        tasks.append(fetch_symbol_data(exchange, symbol, '1m'))
        
    await asyncio.gather(*tasks)
    await exchange.close()
    print("✨ ALL DATA FETCHED")

if __name__ == "__main__":
    asyncio.run(main())
