import asyncio
import logging
import time
from collections import deque

log = logging.getLogger("PerfMonitor")

class PerformanceMonitor:
    """
    Track latency of each model and the ensemble.
    Alerts if any model is slower than threshold.
    """
    
    def __init__(self, window_size=100):
        self.latencies = {
            'RF': deque(maxlen=window_size),
            'XGB': deque(maxlen=window_size),
            'LGB': deque(maxlen=window_size),
            'GB': deque(maxlen=window_size),
            'LSTM': deque(maxlen=window_size),
            'ensemble': deque(maxlen=window_size),
        }
        
        self.thresholds = {
            'RF': 10,        # ms
            'XGB': 50,
            'LGB': 5,
            'GB': 100,
            'LSTM': 500,
            'ensemble': 800,  # Total time for all models
        }
    
    def record_latency(self, model_name: str, latency_ms: float):
        """Record latency for a model"""
        if model_name in self.latencies:
            self.latencies[model_name].append(latency_ms)
            
            # Alert if exceeds threshold
            if latency_ms > self.thresholds[model_name]:
                log.warning(f"⚠️ {model_name} slow: {latency_ms:.1f}ms "
                          f"(threshold: {self.thresholds[model_name]}ms)")
    
    def get_stats(self) -> dict:
        """Get performance statistics"""
        stats = {}
        for model_name, latencies in self.latencies.items():
            if latencies:
                stats[model_name] = {
                    'avg_ms': float(sum(latencies) / len(latencies)),
                    'max_ms': float(max(latencies)),
                    'min_ms': float(min(latencies)),
                    'p95_ms': float(sorted(latencies)[int(len(latencies) * 0.95)])
                }
        return stats
    
    async def log_stats_periodically(self, interval_s=300):
        """Log stats every N seconds"""
        while True:
            await asyncio.sleep(interval_s)
            stats = self.get_stats()
            if stats:
                log.info(f"📊 Performance Stats: {stats}")
