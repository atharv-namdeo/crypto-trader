import sys
import os
import ccxt
import pandas as pd
from datetime import datetime

exchange = ccxt.binance()
symbol = 'BTC/USDT'
since = exchange.parse8601("2025-06-15T00:00:00Z")

print(f"Testing Sync CCXT for {symbol} Since: {since}")
try:
    ohlcv = exchange.fetch_ohlcv(symbol, '1h', since, limit=10)
    if ohlcv:
        print(f"SUCCESS: Fetched {len(ohlcv)} rows.")
        print(f"First row: {ohlcv[0]}")
    else:
        print("FAILED: No data returned from Binance for this date.")
except Exception as e:
    print(f"FAILED: Error connecting or fetching: {e}")
