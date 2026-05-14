import os
import asyncio
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List
import numpy as np
import pandas as pd
from core.state_manager import StateManager

log = logging.getLogger("WeeklyReport")

class WeeklyReportGenerator:
    """Generate comprehensive weekly trading reports"""
    
    def __init__(self, state: StateManager):
        self.state = state
        self.report_dir = 'reports/weekly'
        os.makedirs(self.report_dir, exist_ok=True)
    
    async def generate_weekly_report(self) -> Dict:
        """7-day cumulative metrics"""
        week_end = datetime.now().date()
        week_start = week_end - timedelta(days=7)
        log.info(f"Generating weekly report for {week_start} to {week_end}...")
        
        try:
            report = {
                'week_start': str(week_start),
                'week_end': str(week_end),
                'summary': await self._generate_weekly_summary(week_start, week_end),
                'daily_breakdown': await self._generate_daily_breakdown(),
                'strategy_analysis': await self._generate_strategy_analysis(),
                'optimization_metrics': await self._generate_optimization_metrics(),
            }
            
            # Save report
            report_path = os.path.join(self.report_dir, f"weekly_report_{week_end}.json")
            with open(report_path, 'w') as f:
                json.dump(report, f, indent=2)
            
            log.info(f"✅ Weekly report generated: {report_path}")
            return report
            
        except Exception as e:
            log.error(f"❌ Failed to generate weekly report: {e}")
            return {}

    async def _generate_weekly_summary(self, start, end) -> Dict:
        # Fetch trades from last 7 days from Redis (assuming we store them or can aggregate from daily)
        trades_raw = await self.state.redis.lrange('trade:history:7d', 0, -1)
        trades = [json.loads(t) for t in trades_raw]
        
        if not trades:
            return {'total_pnl': 0, 'trades': 0}
            
        pnls = [float(t.get('pnl', 0)) for t in trades]
        
        return {
            'total_pnl': float(sum(pnls)),
            'total_trades': len(trades),
            'avg_trade_pnl': float(np.mean(pnls)),
            'win_rate_pct': float(len([p for p in pnls if p > 0]) / len(trades) * 100)
        }

    async def _generate_daily_breakdown(self) -> List[Dict]:
        return [] # Simplified for now

    async def _generate_strategy_analysis(self) -> Dict:
        return {}

    async def _generate_optimization_metrics(self) -> List[str]:
        return ["💡 Diversification opportunity: Increase exposure to L2 sector."]
