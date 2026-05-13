"""
fetch_may2026_data.py
Fetches OHLCV data for the Apr 13 - May 13, 2026 backtest window.
Saves to backtest_data_may2026/
"""

import ccxt
import pandas as pd
import os
import time
from datetime import datetime, timezone

DATA_DIR = "backtest_data_may2026"
SYMBOLS = [
    'BTC/USDT', 'ETH/USDT', 'SOL/USDT', 'XRP/USDT',
    'ADA/USDT', 'DOGE/USDT', 'SHIB/USDT', 'POL/USDT',
    'AVAX/USDT', 'LINK/USDT'
]

# Period: Apr 13 2026 00:00 UTC  →  May 13 2026 23:59 UTC
START_DATE = "2026-04-13"
END_DATE   = "2026-05-13"

# For 1d context we pull 300 days of history so SMA-200 indicators are warm
CONTEXT_DAYS_1D = 300
CONTEXT_DAYS_1H = 60   # 60 days of hourly for MACD/EMA warmup

def fetch_range(exchange, symbol, timeframe, since_ms, until_ms):
    """Paginate through Binance until we reach until_ms."""
    all_bars = []
    cur = since_ms
    while cur < until_ms:
        try:
            batch = exchange.fetch_ohlcv(symbol, timeframe, since=cur, limit=1000)
            if not batch:
                break
            all_bars.extend(batch)
            last_ts = batch[-1][0]
            if last_ts >= until_ms:
                break
            cur = last_ts + 1
            time.sleep(exchange.rateLimit / 1000.0)
        except Exception as e:
            print(f"  [WARN] {symbol} {timeframe}: {e}. Retrying in 2s...")
            time.sleep(2)
    return all_bars

def ms(date_str):
    return int(pd.Timestamp(date_str, tz="UTC").timestamp() * 1000)

def main():
    os.makedirs(DATA_DIR, exist_ok=True)
    exchange = ccxt.binance({'enableRateLimit': True})

    until_ms  = ms(END_DATE) + 24 * 3600 * 1000  # inclusive last day
    sim_start = ms(START_DATE)

    for sym in SYMBOLS:
        tag = sym.replace('/', '_')
        print(f"\n=== Fetching {sym} ===")

        # ── 1d (300 days of history for indicator warmup) ─────────────────
        since_1d = sim_start - CONTEXT_DAYS_1D * 86400 * 1000
        bars_1d = fetch_range(exchange, sym, '1d', since_1d, until_ms)
        if bars_1d:
            df = pd.DataFrame(bars_1d, columns=['timestamp','open','high','low','close','volume'])
            df.drop_duplicates('timestamp', inplace=True)
            df.sort_values('timestamp', inplace=True)
            path = f"{DATA_DIR}/{tag}_1d.csv"
            df.to_csv(path, index=False)
            print(f"  1d: {len(df)} bars -> {path}")
        else:
            print(f"  1d: NO DATA")

        # 1h (60 days for warmup + full simulation window)
        since_1h = sim_start - CONTEXT_DAYS_1H * 86400 * 1000
        bars_1h = fetch_range(exchange, sym, '1h', since_1h, until_ms)
        if bars_1h:
            df = pd.DataFrame(bars_1h, columns=['timestamp','open','high','low','close','volume'])
            df.drop_duplicates('timestamp', inplace=True)
            df.sort_values('timestamp', inplace=True)
            path = f"{DATA_DIR}/{tag}_1h.csv"
            df.to_csv(path, index=False)
            print(f"  1h: {len(df)} bars -> {path}")
        else:
            print(f"  1h: NO DATA")

        # 1m (simulation window only)
        bars_1m = fetch_range(exchange, sym, '1m', sim_start, until_ms)
        if bars_1m:
            df = pd.DataFrame(bars_1m, columns=['timestamp','open','high','low','close','volume'])
            df.drop_duplicates('timestamp', inplace=True)
            df.sort_values('timestamp', inplace=True)
            path = f"{DATA_DIR}/{tag}_1m.csv"
            df.to_csv(path, index=False)
            print(f"  1m: {len(df)} bars -> {path}")
        else:
            print(f"  1m: NO DATA (Binance limits old 1m data)")

    print(f"\n✅ All data saved to ./{DATA_DIR}/")

if __name__ == "__main__":
    main()
