import pandas as pd
import numpy as np
import time
import os
import sys
import asyncio
from datetime import datetime
from config import SYMBOLS, INR_RATE
from core.strategies.ai_ensemble_strategy import AIEnsembleStrategy
from core.state_manager import StateManager
from strategies.utils import compute_atr

class MockState(StateManager):
    """Mock state to avoid Redis dependency during backtest."""
    def __init__(self):
        self.data = {}
    async def connect(self): pass
    async def get(self, key): return self.data.get(key)
    async def set(self, key, val): self.data[key] = val
    async def get_float(self, key): return float(self.data.get(key, 0.0))

async def run_advanced_backtest(symbol, days=30):
    print(f"\n🚀 Starting Professional Backtest for {symbol} ({days} days)...")
    
    # 1. Fetch Data (Mocking for now with current main.exchange)
    import main
    limit = days * 24 * 4 # 15m intervals
    data = main.exchange.fetch_ohlcv(symbol, '15m', limit=limit)
    df = pd.DataFrame(data, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
    df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
    
    # 2. Setup Strategy
    state = MockState()
    strategy = AIEnsembleStrategy(state)
    strategy.capital = 1000.0  # $1000 base
    
    trades = []
    equity = [strategy.capital]
    timestamps = [df['timestamp'].iloc[0]]
    
    # 3. Simulation Loop
    for i in range(200, len(df)):
        price = df['close'].iloc[i]
        curr_time = df['timestamp'].iloc[i]
        
        # Mock strategy inputs (df subset)
        # In a real backtest, we'd pass the sliver to strategy.on_candle()
        # For brevity, let's simulate the core logic
        window = df.iloc[i-150:i+1].copy()
        
        # We need to simulate the strategy.on_update() equivalent
        # Since strategy.on_update() is async and does many things, 
        # let's call a simplified version or just mock the score
        # For this refactor, I'll implement a 'backtest_step' in the strategy later
        # But here, let's calculate the PnL of active trades
        pos = await state.get(f"ai_ensemble:pos:{symbol}")
        
        if pos:
            # Check Exit (SL/TP)
            entry = float(pos['entry'])
            side = str(pos['side'])
            sl = float(pos['sl'])
            tp = float(pos['tp'])
            qty = float(pos['qty'])

            pnl = 0
            exit_reason = None
            price_exit = price
            
            if side == 'LONG':
                if df['low'].iloc[i] <= sl:
                    exit_reason = "STOP_LOSS"
                    price_exit = sl
                elif df['high'].iloc[i] >= tp:
                    exit_reason = "TAKE_PROFIT"
                    price_exit = tp
                if exit_reason:
                    pnl = (price_exit - entry) * qty
            else:
                if df['high'].iloc[i] >= sl:
                    exit_reason = "STOP_LOSS"
                    price_exit = sl
                elif df['low'].iloc[i] <= tp:
                    exit_reason = "TAKE_PROFIT"
                    price_exit = tp
                if exit_reason:
                    pnl = (entry - price_exit) * qty

            if exit_reason:
                strategy.capital += pnl
                trades.append({
                    'symbol': symbol,
                    'side': side,
                    'entry': entry,
                    'exit': price_exit,
                    'pnl': pnl,
                    'pnl_pct': (pnl / (entry * qty)) * 100,
                    'reason': exit_reason,
                    'time': curr_time
                })
                await state.set(f"ai_ensemble:pos:{symbol}", None)
        
        # Simplified signal (every 50 candles for demo, replace with actual strategy call)
        if not pos and i % 40 == 0:
            # Mock a signal
            side = 'LONG' if i % 80 == 0 else 'SHORT'
            atr = compute_atr(window, 14).iloc[-1]
            sl = price - (atr * 2) if side == 'LONG' else price + (atr * 2)
            tp = price + (atr * 4) if side == 'LONG' else price - (atr * 4)
            qty = (strategy.capital * 0.1) / price # 10% allocation
            
            await state.set(f"ai_ensemble:pos:{symbol}", {
                'side': side, 'entry': price, 'sl': sl, 'tp': tp, 'qty': qty
            })

        equity.append(strategy.capital)
        timestamps.append(curr_time)

    # 4. Calculate Metrics
    if not trades:
        print("No trades found.")
        return

    df_trades = pd.DataFrame(trades)
    win_rate = len(df_trades[df_trades['pnl'] > 0]) / len(df_trades)
    gross_profit = df_trades[df_trades['pnl'] > 0]['pnl'].sum()
    gross_loss = abs(df_trades[df_trades['pnl'] < 0]['pnl'].sum())
    profit_factor = gross_profit / gross_loss if gross_loss > 0 else float('inf')
    
    # Sharpe Ratio (Daily-ish)
    returns = pd.Series(equity).pct_change().dropna()
    sharpe = (returns.mean() / returns.std()) * np.sqrt(252 * 96) if returns.std() > 0 else 0
    
    # Max Drawdown
    equity_ser = pd.Series(equity)
    drawdown = (equity_ser.cummax() - equity_ser) / equity_ser.cummax()
    max_dd = drawdown.max()

    print(f"\n📊 PERFORMANCE SUMMARY: {symbol}")
    print(f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    print(f"Total Trades:    {len(df_trades)}")
    print(f"Win Rate:        {win_rate:.2%}")
    print(f"Profit Factor:   {profit_factor:.2f}")
    print(f"Sharpe Ratio:    {sharpe:.2f}")
    print(f"Max Drawdown:    {max_dd:.2%}")
    print(f"Final Capital:   ${strategy.capital:.2f} (₹{strategy.capital * INR_RATE:,.2f})")
    print(f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n")

if __name__ == "__main__":
    for sym in SYMBOLS:
        asyncio.run(run_advanced_backtest(sym))
