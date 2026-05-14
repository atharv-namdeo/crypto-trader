import os
import asyncio
import json
import logging
from datetime import datetime
from typing import Dict, List
import numpy as np
import pandas as pd
from core.state_manager import StateManager

log = logging.getLogger("DailyReport")

class DailyReportGenerator:
    """Generate comprehensive daily trading reports"""
    
    def __init__(self, state: StateManager):
        self.state = state
        self.report_dir = 'reports/daily'
        os.makedirs(self.report_dir, exist_ok=True)
    
    async def generate_daily_report(self) -> Dict:
        """Generate complete daily report"""
        
        report_date = datetime.now().date()
        log.info(f"Generating daily report for {report_date}...")
        
        try:
            report = {
                'date': str(report_date),
                'generated_at': datetime.now().isoformat(),
                'summary': await self._generate_summary(),
                'performance': await self._generate_performance_metrics(),
                'trades': await self._generate_trade_analysis(),
                'ml_signals': await self._generate_ml_analysis(),
                'risk_metrics': await self._generate_risk_analysis(),
                'portfolio': await self._generate_portfolio_snapshot(),
                'alerts': await self._generate_alert_summary(),
                'recommendations': await self._generate_recommendations(),
            }
            
            # Save report JSON
            report_path = os.path.join(self.report_dir, f"daily_report_{report_date}.json")
            with open(report_path, 'w') as f:
                json.dump(report, f, indent=2)
            
            # Generate and save HTML
            html_report = self._generate_html_report(report)
            html_path = os.path.join(self.report_dir, f"daily_report_{report_date}.html")
            with open(html_path, 'w') as f:
                f.write(html_report)
            
            log.info(f"✅ Daily report generated: {html_path}")
            return report
            
        except Exception as e:
            log.error(f"❌ Failed to generate report: {e}")
            return {}

    async def _generate_summary(self) -> Dict:
        equity = await self.state.get_float('portfolio:value') or 0.0
        starting_equity = await self.state.get_float('portfolio:starting_value') or equity
        
        trades_24h_raw = await self.state.redis.lrange('trade:history:24h', 0, -1)
        trades_24h = [json.loads(t) for t in trades_24h_raw]
        
        daily_pnl = sum(float(t.get('pnl', 0)) for t in trades_24h)
        daily_return = (daily_pnl / equity * 100) if equity > 0 else 0.0
        
        return {
            'account_equity': float(equity),
            'daily_pnl': float(daily_pnl),
            'daily_return_pct': float(daily_return),
            'total_trades': len(trades_24h)
        }

    async def _generate_performance_metrics(self) -> Dict:
        trades_raw = await self.state.redis.lrange('trade:history:24h', 0, -1)
        trades = [json.loads(t) for t in trades_raw]
        
        if not trades:
            return {'win_rate': 0, 'profit_factor': 0}
            
        pnls = [float(t.get('pnl', 0)) for t in trades]
        wins = [p for p in pnls if p > 0]
        losses = [abs(p) for p in pnls if p < 0]
        
        win_rate = (len(wins) / len(trades)) * 100
        profit_factor = sum(wins) / sum(losses) if sum(losses) > 0 else float('inf')
        
        return {
            'win_rate_pct': float(win_rate),
            'profit_factor': float(profit_factor),
            'avg_win': float(np.mean(wins)) if wins else 0.0,
            'avg_loss': float(np.mean(losses)) if losses else 0.0
        }

    async def _generate_trade_analysis(self) -> Dict:
        trades_raw = await self.state.redis.lrange('trade:history:24h', 0, -1)
        trades = [json.loads(t) for t in trades_raw]
        
        by_strategy = {}
        for t in trades:
            strat = t.get('strategy', 'UNKNOWN')
            pnl = float(t.get('pnl', 0))
            if strat not in by_strategy:
                by_strategy[strat] = {'count': 0, 'pnl': 0.0}
            by_strategy[strat]['count'] += 1
            by_strategy[strat]['pnl'] += pnl
            
        return {'by_strategy': by_strategy}

    async def _generate_ml_analysis(self) -> Dict:
        accuracy = await self.state.get_float('ml:signal_accuracy:24h') or 0.0
        return {'avg_accuracy_pct': float(accuracy * 100)}

    async def _generate_risk_analysis(self) -> Dict:
        drawdown = await self.state.get_float('portfolio:drawdown') or 0.0
        return {'current_drawdown_pct': float(drawdown * 100)}

    async def _generate_portfolio_snapshot(self) -> Dict:
        positions = await self.state.get('portfolio:positions') or '{}'
        if isinstance(positions, str):
            positions = json.loads(positions)
        return {'positions': positions}

    async def _generate_alert_summary(self) -> Dict:
        alerts_raw = await self.state.redis.lrange('alerts:history:24h', 0, -1)
        return {'total_alerts': len(alerts_raw)}

    async def _generate_recommendations(self) -> List[str]:
        summary = await self._generate_summary()
        perf = await self._generate_performance_metrics()
        
        recs = []
        if perf['win_rate_pct'] < 50:
            recs.append("⚠️ Win rate is below 50%. Review entry filters.")
        if summary['daily_pnl'] < 0:
            recs.append("📉 Daily loss detected. Consider reducing position sizes.")
        if not recs:
            recs.append("✅ System performing within parameters.")
        return recs

    def _generate_html_report(self, report: Dict) -> str:
        s = report['summary']
        p = report['performance']
        
        html = f"""
        <html>
        <head>
            <style>
                body {{ font-family: 'Inter', sans-serif; background: #0a0a0b; color: #fff; padding: 40px; }}
                .card {{ background: #141416; border: 1px solid #232326; padding: 20px; border-radius: 12px; margin-bottom: 20px; }}
                h1 {{ color: #00ff9d; }}
                .metric {{ font-size: 24px; font-weight: bold; }}
                .green {{ color: #00ff9d; }}
                .red {{ color: #ff4d4d; }}
            </style>
        </head>
        <body>
            <h1>📊 Daily Trading Report: {report['date']}</h1>
            <div class="card">
                <h2>Account Summary</h2>
                <p>Equity: <span class="metric">${s['account_equity']:,.2f}</span></p>
                <p>Daily P&L: <span class="metric {('green' if s['daily_pnl'] >= 0 else 'red')}">${s['daily_pnl']:,.2f}</span></p>
                <p>Return: {s['daily_return_pct']:.2f}%</p>
            </div>
            <div class="card">
                <h2>Performance</h2>
                <p>Win Rate: {p['win_rate_pct']:.1f}%</p>
                <p>Profit Factor: {p['profit_factor']:.2f}</p>
            </div>
            <div class="card">
                <h2>Recommendations</h2>
                <ul>
                    {''.join([f"<li>{r}</li>" for r in report['recommendations']])}
                </ul>
            </div>
        </body>
        </html>
        """
        return html
