import asyncio
import json
import logging
from reporting.daily_report_generator import DailyReportGenerator
from core.state_manager import StateManager

logging.basicConfig(level=logging.INFO)

async def test_reporting():
    state = StateManager()
    await state.connect()
    
    # Mock some data in Redis for the report
    await state.redis.set('portfolio:value', 12500.50)
    await state.redis.set('pnl:24h', 450.25)
    await state.redis.lpush('trade:history:24h', json.dumps({
        "symbol": "BTC/USDT", "strategy": "SCALPER", "pnl": 50.5, "time": "2026-03-24T12:00:00"
    }))
    
    gen = DailyReportGenerator(state)
    report = await gen.generate_daily_report()
    
    print("\n--- TEST REPORT SUMMARY ---")
    print(f"Date: {report.get('date')}")
    print(f"Equity: ${report.get('summary', {}).get('account_equity')}")
    print(f"Daily P&L: ${report.get('summary', {}).get('daily_pnl')}")
    print(f"Total Alerts: {report.get('alerts', {}).get('total_alerts')}")
    print("---------------------------\n")
    
    await state.disconnect()

if __name__ == "__main__":
    asyncio.run(test_reporting())
