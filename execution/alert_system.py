import logging
import os
import json
import asyncio
from datetime import datetime
from core.state_manager import StateManager

log = logging.getLogger("AlertSystem")

class AlertSystem:
    """
    Multi-channel alert system for critical events.
    Integrates with Telegram (primary) and logs to Redis for Dashboard.
    """
    
    def __init__(self, state: StateManager):
        self.state = state
        self.telegram_token = os.getenv('TELEGRAM_BOT_TOKEN')
        self.telegram_chat_id = os.getenv('TELEGRAM_CHAT_ID')
    
    async def send_alert(self, level: str, title: str, message: str, data: dict = None):
        """Send alert through all channels"""
        timestamp = datetime.now().isoformat()
        alert_data = {
            'timestamp': timestamp,
            'level': level, # CRITICAL, HIGH, MEDIUM, INFO
            'title': title,
            'message': message,
            'data': data or {}
        }
        
        # 1. Log to Redis for Dashboard audit trail
        try:
            await self.state.redis.lpush('alerts:history', json.dumps(alert_data))
            await self.state.redis.ltrim('alerts:history', 0, 99)
        except Exception as e:
            log.error(f"Failed to log alert to Redis: {e}")
            
        # 2. Send to Telegram (Real-time)
        if self.telegram_token and self.telegram_chat_id:
            try:
                await self._send_telegram(alert_data)
            except Exception as e:
                log.error(f"Failed to send Telegram alert: {e}")
                
        # 3. Log to file
        log.warning(f"[{level}] {title}: {message}")

    async def _send_telegram(self, alert: dict):
        """Minimal Telegram sender using aiohttp or similar"""
        import aiohttp
        
        icon = "🚨" if alert['level'] == 'CRITICAL' else "⚠️" if alert['level'] == 'HIGH' else "ℹ️"
        text = (
            f"{icon} *{alert['level']} ALERT*\n"
            f"*{alert['title']}*\n\n"
            f"{alert['message']}\n\n"
            f"Time: `{alert['timestamp']}`"
        )
        
        url = f"https://api.telegram.org/bot{self.telegram_token}/sendMessage"
        payload = {
            'chat_id': self.telegram_chat_id,
            'text': text,
            'parse_mode': 'Markdown'
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=payload) as resp:
                if resp.status != 200:
                    log.error(f"Telegram API error: {await resp.text()}")

async def monitor_critical_metrics(state: StateManager, alert_system: AlertSystem):
    """Background task to monitor system health and trigger alerts"""
    while True:
        try:
            # 1. Check drawdown
            val = await state.get_float('portfolio:value')
            peak = await state.get_float('portfolio:peak') or val
            if val > peak:
                await state.set('portfolio:peak', val)
                peak = val
                
            if peak > 0:
                drawdown = (peak - val) / peak
                if drawdown > 0.15: # 15% drawdown alert
                    await alert_system.send_alert(
                        'CRITICAL',
                        'Excessive Drawdown',
                        f'Portfolio drawdown is {drawdown:.2%}.',
                        {'current_val': val, 'peak_val': peak}
                    )
            
            # 2. Check for recent errors
            error_count = await state.get('metrics:error_count:5m') or 0
            if int(error_count) > 10:
                await alert_system.send_alert(
                    'HIGH',
                    'High Error Rate',
                    f'{error_count} errors detected in the last 5 minutes.',
                )
                await state.set('metrics:error_count:5m', 0) # reset after alert
                
            await asyncio.sleep(60) # Check every minute
            
        except Exception as e:
            log.error(f"Alert monitoring error: {e}")
            await asyncio.sleep(60)
