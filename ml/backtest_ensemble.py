import pandas as pd
import numpy as np
import asyncio
import logging
import ccxt
import os
from datetime import datetime
from core.state_manager import StateManager
from ml.parallel_predictor import ParallelMLPredictor

log = logging.getLogger("EnsembleBacktest")

class EnsembleBacktester:
    """
    Backtest the ML ensemble on historical data.
    Validates win rate, Sharpe ratio, max drawdown before live trading.
    """
    
    def __init__(self, state: StateManager, ml_predictor: ParallelMLPredictor):
        self.state = state
        self.ml = ml_predictor
        self.trades = []
    
    async def backtest_period(self, symbol: str, start_date: str, end_date: str):
        """
        Backtest ML ensemble from start_date to end_date.
        """
        log.info(f"🔄 Backtesting {symbol} from {start_date} to {end_date}...")
        
        # Fetch historical data (using ccxt for convenience in backtest)
        exchange = ccxt.binance()
        since = exchange.parse8601(f"{start_date}T00:00:00Z")
        ohlcv = exchange.fetch_ohlcv(symbol, timeframe='1h', since=since, limit=1000)
        df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
        
        capital = 1000.0  # Starting capital
        position = None
        equity_curve = [capital]
        
        for idx in range(20, len(df)):  # Start after warmup
            current_row = df.iloc[idx]
            current_price = float(current_row['close'])
            
            # Generate ML prediction
            features = {
                'open': float(current_row['open']),
                'high': float(current_row['high']),
                'low': float(current_row['low']),
                'close': float(current_row['close']),
                'volume': float(current_row['volume']),
            }
            
            prediction = await self.ml.predict_all(features, symbol)
            signal = prediction['signal']
            confidence = prediction['confidence']
            
            # Trading logic
            if signal == 'BUY' and not position and confidence > 0.65:
                position = {
                    'entry_price': current_price,
                    'entry_time': current_row['timestamp'],
                    'side': 'LONG'
                }
                log.info(f"✅ BUY at {current_price:.2f} (confidence: {confidence:.2%})")
            
            elif signal == 'SELL' and position and position['side'] == 'LONG':
                # Exit position
                pnl = (current_price - position['entry_price']) / position['entry_price']
                capital = capital * (1 + pnl * 0.95)  # 95% allocation
                
                duration = (current_row['timestamp'] - position['entry_time']).total_seconds() / 3600
                
                self.trades.append({
                    'entry_price': position['entry_price'],
                    'exit_price': current_price,
                    'pnl_pct': pnl * 100,
                    'duration_h': duration,
                    'signal_confidence': confidence,
                })
                
                log.info(f"❌ SELL at {current_price:.2f} | PnL: {pnl*100:.2f}%")
                position = None
            
            equity_curve.append(capital)
        
        # Calculate metrics
        metrics = self._calculate_metrics(equity_curve)
        log.info(f"📊 Backtest Results for {symbol}:\n{metrics}")
        
        return {
            'trades': self.trades,
            'equity_curve': equity_curve,
            'metrics': metrics
        }
    
    def _calculate_metrics(self, equity_curve: list) -> dict:
        """Calculate trading metrics"""
        returns = np.diff(equity_curve) / equity_curve[:-1]
        
        total_return = (equity_curve[-1] - equity_curve[0]) / equity_curve[0]
        sharpe = np.mean(returns) / (np.std(returns) + 1e-9) * np.sqrt(252 * 24) # Adjust for hourly data
        
        # Max Drawdown
        peaks = np.maximum.accumulate(equity_curve)
        drawdowns = (peaks - equity_curve) / peaks
        max_dd = np.max(drawdowns)
        
        winning_trades = sum(1 for t in self.trades if t['pnl_pct'] > 0)
        total_trades = len(self.trades)
        win_rate = winning_trades / total_trades if total_trades > 0 else 0
        
        return {
            'total_return_pct': total_return * 100,
            'sharpe_ratio': sharpe,
            'max_drawdown_pct': max_dd * 100,
            'win_rate_pct': win_rate * 100,
            'total_trades': total_trades,
            'avg_trade_duration_h': np.mean([t['duration_h'] for t in self.trades]) if self.trades else 0,
        }

if __name__ == "__main__":
    # Quick test runner if called directly
    async def test():
        from core.state_manager import StateManager
        state = StateManager()
        await state.connect()
        ml = ParallelMLPredictor(state)
        bt = EnsembleBacktester(state, ml)
        await bt.backtest_period('BTC/USDT', '2024-03-01', '2024-03-24')
    
    asyncio.run(test())
