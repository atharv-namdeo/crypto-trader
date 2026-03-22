import asyncio
import logging
from core.state_manager import StateManager
from core.telegram_notifier import TelegramNotifier

log = logging.getLogger("RiskGuardian")

class RiskGuardian:
    def __init__(self, state: StateManager):
        self.state = state
        self.telegram = TelegramNotifier()
        self.running = False

    async def run_loop(self, interval=60):
        self.running = True
        log.info("🛡️ RiskGuardian active")
        while self.running:
            try:
                await self.check_risks()
            except Exception as e:
                log.error(f"RiskGuardian error: {e}")
            await asyncio.sleep(interval)

    async def check_risks(self):
        portfolio_value = await self.state.get_float('portfolio:value') or 1000.0
        daily_pnl = await self.state.get_float('pnl:24h') or 0.0
        
        # 1. Alert if portfolio drops more than 5% in a day
        if daily_pnl < -(portfolio_value * 0.05):
            await self.telegram.alert(
                '⚠️ Daily Loss Limit Warning',
                f'Portfolio down ${abs(daily_pnl):.2f} today. '
                f'Consider pausing trading.',
                level='WARNING'
            )

        # 2. Alert if win rate drops below 40% after 10+ trades
        stats = await self.state.get('portfolio:stats') or {}
        total_trades = stats.get('total_trades', 0)
        win_rate = stats.get('win_rate', 0)
        
        if total_trades >= 10 and win_rate < 40:
            await self.telegram.alert(
                '📉 Low Win Rate Alert',
                f'Win rate is {win_rate:.1f}% after {total_trades} trades. '
                f'Strategy may need adjustment.',
                level='WARNING'
            )
