from prometheus_client import Gauge, Histogram, Counter, generate_latest, CollectorRegistry
import logging
import asyncio
from core.state_manager import StateManager

log = logging.getLogger("Prometheus")

class PrometheusMetricsExporter:
    """Export trading metrics to Prometheus"""
    
    def __init__(self):
        self.registry = CollectorRegistry()
        
        # Account metrics
        self.account_equity = Gauge('trader_equity_usdt', 'Account Equity', registry=self.registry)
        self.daily_pnl = Gauge('trader_daily_pnl_usdt', 'Daily P&L', registry=self.registry)
        self.drawdown = Gauge('trader_drawdown_pct', 'Current Drawdown %', registry=self.registry)
        
        # ML metrics
        self.ml_accuracy = Gauge('trader_ml_accuracy', 'ML Accuracy %', registry=self.registry)
        self.prediction_latency = Histogram(
            'trader_ml_latency_ms', 'ML Latency', 
            buckets=(10, 50, 100, 200, 500), 
            registry=self.registry
        )
        
        # System metrics
        self.api_errors = Counter('trader_api_errors_total', 'API Errors', ['exchange'], registry=self.registry)

    async def update_loop(self, state: StateManager):
        """Update metrics from Redis periodically."""
        while True:
            try:
                equity = await state.get_float('portfolio:value') or 0.0
                pnl = await state.get_float('pnl:24h') or 0.0
                dd = await state.get_float('portfolio:drawdown') or 0.0
                acc = await state.get_float('ml:signal_accuracy:24h') or 0.0
                
                self.account_equity.set(equity)
                self.daily_pnl.set(pnl)
                self.drawdown.set(dd * 100)
                self.ml_accuracy.set(acc * 100)
                
            except Exception as e:
                log.error(f"Error updating Prometheus: {e}")
            
            await asyncio.sleep(15)

    def get_metrics(self) -> str:
        return generate_latest(self.registry).decode('utf-8')
