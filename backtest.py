import pandas as pd
import time
import main
from config import SYMBOLS, INR_RATE

def fetch_historical_data(symbol, timeframe='15m', limit=1000):
    print(f"Downloading historical data for {symbol}...")
    exchange = main.exchange
    data = exchange.fetch_ohlcv(symbol, timeframe, limit=limit)
    df = pd.DataFrame(data, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
    df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
    return df

def run_backtest(symbol):
    df = fetch_historical_data(symbol, limit=2000)
    
    trades = []
    active_trade = None
    
    print(f"Starting simulation on {len(df)} candles for {symbol}...\n")
    
    # Start iterating from an index that has enough history (e.g., 200)
    for i in range(200, len(df)):
        current_time = df['timestamp'].iloc[i]
        
        # If we have an active trade, check if it hits SL or TP during this candle
        if active_trade:
            current_low = df['low'].iloc[i]
            current_high = df['high'].iloc[i]
            
            if active_trade['direction'] == 'LONG':
                if current_low <= active_trade['sl']:
                    active_trade['exit_price'] = active_trade['sl']
                    active_trade['exit_time'] = current_time
                    active_trade['pnl'] = (active_trade['exit_price'] - active_trade['entry']) * active_trade['qty']
                    trades.append(active_trade)
                    print(f"[{current_time}] 🛑 STOP LOSS hit for LONG at ₹{active_trade['sl'] * INR_RATE:,.2f} (PnL: ₹{active_trade['pnl'] * INR_RATE:,.2f})")
                    active_trade = None
                    continue
                elif current_high >= active_trade['tp']:
                    active_trade['exit_price'] = active_trade['tp']
                    active_trade['exit_time'] = current_time
                    active_trade['pnl'] = (active_trade['exit_price'] - active_trade['entry']) * active_trade['qty']
                    trades.append(active_trade)
                    print(f"[{current_time}] 🎯 TAKE PROFIT hit for LONG at ₹{active_trade['tp'] * INR_RATE:,.2f} (PnL: ₹{active_trade['pnl'] * INR_RATE:,.2f})")
                    active_trade = None
                    continue
            else:
                if current_high >= active_trade['sl']:
                    active_trade['exit_price'] = active_trade['sl']
                    active_trade['exit_time'] = current_time
                    active_trade['pnl'] = (active_trade['entry'] - active_trade['exit_price']) * active_trade['qty']
                    trades.append(active_trade)
                    print(f"[{current_time}] 🛑 STOP LOSS hit for SHORT at ₹{active_trade['sl'] * INR_RATE:,.2f} (PnL: ₹{active_trade['pnl'] * INR_RATE:,.2f})")
                    active_trade = None
                    continue
                elif current_low <= active_trade['tp']:
                    active_trade['exit_price'] = active_trade['tp']
                    active_trade['exit_time'] = current_time
                    active_trade['pnl'] = (active_trade['entry'] - active_trade['exit_price']) * active_trade['qty']
                    trades.append(active_trade)
                    print(f"[{current_time}] 🎯 TAKE PROFIT hit for SHORT at ₹{active_trade['tp'] * INR_RATE:,.2f} (PnL: ₹{active_trade['pnl'] * INR_RATE:,.2f})")
                    active_trade = None
                    continue
                    
        # If no active trade, look for a new signal
        if not active_trade:
            # Mock fetch_ohlcv to return the window up to current index
            def mock_fetch(s, timeframe_='15m', limit_=200):
                # Return the last 'limit_' candles up to index 'i'
                window = df.iloc[i-limit_+1:i+1].copy()
                window.reset_index(drop=True, inplace=True)
                return window
            
            # Patch the fetch function in main module
            original_fetch = main.fetch_ohlcv
            main.fetch_ohlcv = mock_fetch
            
            # Temporarily disable printing from main.py
            import sys, os
            old_stdout = sys.stdout
            sys.stdout = open(os.devnull, 'w')
            
            try:
                signal = main.analyze(symbol)
            finally:
                sys.stdout.close()
                sys.stdout = old_stdout
            
            # Restore original fetch function
            main.fetch_ohlcv = original_fetch
            
            if signal:
                active_trade = signal.copy()
                active_trade['entry_time'] = current_time
                print(f"[{current_time}] 🟢 ENTER {active_trade['direction']} at ₹{active_trade['entry'] * INR_RATE:,.2f} | SL: ₹{active_trade['sl'] * INR_RATE:,.2f} | TP: ₹{active_trade['tp'] * INR_RATE:,.2f}")

    # Final Metrics
    if trades:
        wins = [t for t in trades if t['pnl'] > 0]
        profit = sum(t['pnl'] for t in trades)
        win_rate = len(wins) / len(trades)
        print(f"\n==== Backtest Results: {symbol} ====")
        print(f"Total Trades: {len(trades)}")
        print(f"Win Rate:     {win_rate:.2%}")
        print(f"Total PnL:    ₹{profit * INR_RATE:,.2f}\n")
    else:
        print(f"\n==== Backtest Results: {symbol} ====")
        print("No trades triggered in this period.\n")

if __name__ == "__main__":
    for sym in SYMBOLS:
        run_backtest(sym)
