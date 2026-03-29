import os
import asyncio
import logging
from telegram import Bot
from telegram.error import TelegramError

class TelegramNotifier:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(TelegramNotifier, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized: return
        self.token = os.getenv('TELEGRAM_BOT_TOKEN')
        self.chat_id = os.getenv('TELEGRAM_CHAT_ID')
        self.bot = Bot(token=self.token) if self.token else None
        self.log = logging.getLogger('Telegram')
        self.enabled = bool(self.token and self.chat_id)
        self._initialized = True
    
    async def verify_connection(self):
        if not self.enabled:
            self.log.warning("Telegram not configured — skipping")
            return False
        try:
            await self.bot.send_message(
                chat_id=self.chat_id,
                text="🤖 QuantBot connected successfully!"
            )
            self.log.info("✅ Telegram connected")
            return True
        except Exception as e:
            self.log.error(f"Telegram verify failed: {e}")
            self.log.error("Make sure you sent /start to your bot first")
            return False

    async def send(self, message: str):
        if not self.enabled:
            return
        try:
            await self.bot.send_message(
                chat_id=self.chat_id,
                text=message,
                parse_mode='HTML'
            )
        except TelegramError as e:
            self.log.error(f"Telegram send failed: {e}")
    
    async def trade_opened(self, strategy, symbol, side, 
                           entry, qty, stop, tp, conviction):
        emoji = '🟢' if side == 'LONG' else '🔴'
        arrow = '▲' if side == 'LONG' else '▼'
        msg = (
            f"{emoji} <b>TRADE OPENED</b>\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"📊 Strategy: <b>{strategy}</b>\n"
            f"💱 Symbol: <b>{symbol}</b>\n"
            f"📈 Side: <b>{arrow} {side}</b>\n"
            f"💰 Entry: <b>${entry:,.2f}</b>\n"
            f"📦 Qty: <b>{qty:.6f}</b>\n"
            f"🛑 Stop Loss: <b>${stop:,.2f}</b>\n"
            f"🎯 Take Profit: <b>${tp:,.2f}</b>\n"
            f"💪 Conviction: <b>{conviction:.2f}</b>\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"🤖 QuantBot v8.1 | Top 50 Active"
        )
        await self.send(msg)
    
    async def trade_closed(self, strategy, symbol, side,
                           entry, exit_price, qty, pnl, reason, duration):
        if pnl >= 0:
            emoji = '✅'
            pnl_emoji = '📈'
        else:
            emoji = '❌'
            pnl_emoji = '📉'
        
        pnl_pct = (pnl / (entry * qty + 1e-9)) * 100 if entry and qty else 0
        
        msg = (
            f"{emoji} <b>TRADE CLOSED</b>\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"📊 Strategy: <b>{strategy}</b>\n"
            f"💱 Symbol: <b>{symbol}</b>\n"
            f"📈 Side: <b>{side}</b>\n"
            f"🔵 Entry: <b>${entry:,.2f}</b>\n"
            f"🔴 Exit: <b>${exit_price:,.2f}</b>\n"
            f"{pnl_emoji} PnL: <b>${pnl:+.4f} ({pnl_pct:+.2f}%)</b>\n"
            f"⏱ Duration: <b>{duration}</b>\n"
            f"📋 Reason: <b>{reason}</b>\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"🤖 QuantBot v6.0 | PAPER"
        )
        await self.send(msg)
    
    async def daily_summary(self, portfolio_value, daily_pnl,
                            total_trades, win_rate, best_trade,
                            worst_trade, scalper_pnl,
                            swing_pnl, position_pnl):
        emoji = '📈' if daily_pnl >= 0 else '📉'
        msg = (
            f"📊 <b>DAILY SUMMARY</b>\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"💼 Portfolio: <b>${portfolio_value:,.2f}</b>\n"
            f"{emoji} Day PnL: <b>${daily_pnl:+.4f}</b>\n"
            f"🎯 Win Rate: <b>{win_rate:.1f}%</b>\n"
            f"📦 Total Trades: <b>{total_trades}</b>\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"⚡ Scalper PnL: <b>${scalper_pnl:+.4f}</b>\n"
            f"🌊 Swing PnL:   <b>${swing_pnl:+.4f}</b>\n"
            f"🏔 Position PnL: <b>${position_pnl:+.4f}</b>\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"🏆 Best Trade:  <b>${best_trade:+.4f}</b>\n"
            f"💀 Worst Trade: <b>${worst_trade:+.4f}</b>\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"🤖 QuantBot v6.0 | PAPER"
        )
        await self.send(msg)
    
    async def alert(self, title, message, level='INFO'):
        emoji = {'INFO': 'ℹ️', 'WARNING': '⚠️', 'ERROR': '🚨'}.get(level, 'ℹ️')
        msg = (
            f"{emoji} <b>{title}</b>\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"{message}\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"🤖 QuantBot v8.1"
        )
        await self.send(msg)
    
    async def bot_started(self, portfolio_value):
        msg = (
            f"🚀 <b>QUANTBOT STARTED</b>\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"💼 Portfolio: <b>${portfolio_value:,.2f}</b>\n"
            f"⚡ Scalper: <b>Active</b>\n"
            f"🌊 Swing: <b>Active</b>\n"
            f"🏔 Position: <b>Active</b>\n"
            f"📊 Mode: <b>PAPER TRADING (Demo)</b>\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"All 50+ symbols monitored ✅"
        )
        await self.send(msg)
