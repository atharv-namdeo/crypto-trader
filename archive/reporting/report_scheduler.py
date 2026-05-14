import logging
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from reporting.daily_report_generator import DailyReportGenerator
from reporting.weekly_report_generator import WeeklyReportGenerator
from core.state_manager import StateManager

log = logging.getLogger("Scheduler")

class ReportScheduler:
    """Schedule automated reports"""
    
    def __init__(self, state: StateManager):
        self.state = state
        self.scheduler = AsyncIOScheduler()
        self.daily_gen = DailyReportGenerator(state)
        self.weekly_gen = WeeklyReportGenerator(state)
    
    def start(self):
        """Start scheduler"""
        
        # Daily report: Every day at 00:05 UTC
        self.scheduler.add_job(
            self.daily_gen.generate_daily_report,
            'cron',
            hour=0,
            minute=5,
            id='daily_report'
        )
        
        # Weekly report: Monday 01:00 UTC
        self.scheduler.add_job(
            self.weekly_gen.generate_weekly_report,
            'cron',
            day_of_week='mon',
            hour=1,
            minute=0,
            id='weekly_report'
        )
        
        self.scheduler.start()
        log.info("✅ Report scheduler started (00:05 Daily, Mon 01:00 Weekly)")
