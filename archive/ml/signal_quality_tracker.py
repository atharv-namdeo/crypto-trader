import asyncio
import logging
import time
import json
from core.state_manager import StateManager

log = logging.getLogger("SignalQuality")

class SignalQualityTracker:
    """
    Track how accurate the ML signals are in real-time.
    Compare predicted direction vs actual direction after 1h, 4h, 1d.
    """
    
    def __init__(self, state: StateManager):
        self.state = state
        self.pending_signals = {}  # {signal_id: {prediction, entry_time, entry_price}}
    
    async def record_signal(self, symbol: str, signal: str, confidence: float, 
                           price: float, timestamp: float):
        """Record a new ML signal"""
        signal_id = f"{symbol}_{timestamp}"
        
        self.pending_signals[signal_id] = {
            'symbol': symbol,
            'signal': signal,
            'confidence': confidence,
            'entry_price': price,
            'entry_time': timestamp,
            'evaluation_results': {}
        }
        
        # Schedule evaluation at 1h, 4h, 1d
        asyncio.create_task(self._evaluate_signal(signal_id, 3600))      # 1h
        asyncio.create_task(self._evaluate_signal(signal_id, 14400))     # 4h
        asyncio.create_task(self._evaluate_signal(signal_id, 86400))     # 1d
    
    async def _evaluate_signal(self, signal_id: str, delay_s: int):
        """Check if signal was correct after delay_s seconds"""
        await asyncio.sleep(delay_s)
        
        if signal_id not in self.pending_signals:
            return
        
        signal = self.pending_signals[signal_id]
        symbol = signal['symbol']
        entry_price = signal['entry_price']
        expected_dir = signal['signal']  # 'BUY' or 'SELL'
        
        if expected_dir == 'HOLD':
            return

        # Get current price
        current_price = await self.state.get_float(f"price:{symbol}")
        
        if not current_price:
            return
        
        # Determine actual direction
        actual_direction = 'UP' if current_price > entry_price else 'DOWN'
        signal_correct = (
            (expected_dir == 'BUY' and actual_direction == 'UP') or
            (expected_dir == 'SELL' and actual_direction == 'DOWN')
        )
        
        # Record result
        signal['evaluation_results'][delay_s] = {
            'correct': signal_correct,
            'price_change_pct': (current_price - entry_price) / entry_price * 100,
            'evaluated_at': time.time()
        }
        
        # Log
        label = f"{delay_s//3600}h" if delay_s >= 3600 else f"{delay_s//60}m"
        log.info(f"📈 Signal [{signal_id}] @ {label}: "
                f"Predicted {expected_dir}, Actual {actual_direction} "
                f"→ {'✅ CORRECT' if signal_correct else '❌ WRONG'}")
        
        # If all evaluations done, clean up and log aggregate
        if len(signal['evaluation_results']) == 3:
            await self._log_signal_aggregate(signal_id)
            del self.pending_signals[signal_id]
    
    async def _log_signal_aggregate(self, signal_id: str):
        """Aggregate results for a signal"""
        signal = self.pending_signals.get(signal_id)
        if not signal:
            return
        
        results = signal['evaluation_results']
        accuracy = sum(1 for r in results.values() if r['correct']) / len(results)
        
        log.info(f"🎯 Signal [{signal_id}] Final Accuracy: {accuracy*100:.0f}% "
                f"(Confidence: {signal['confidence']:.2%})")
        
        # Store in Redis for dashboard
        await self.state.redis.lpush('signal_quality:history', 
            json.dumps({
                'signal_id': signal_id,
                'accuracy': accuracy,
                'confidence': signal['confidence'],
                'timestamp': time.time()
            })
        )
        await self.state.redis.ltrim('signal_quality:history', 0, 99)
