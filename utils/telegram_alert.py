import requests
import os
from dotenv import load_dotenv

load_dotenv()


def send_alert(signal):
    """Send a formatted trade alert to Telegram."""
    token = os.getenv('TELEGRAM_BOT_TOKEN')
    chat_id = os.getenv('TELEGRAM_CHAT_ID')

    if not token or not chat_id:
        print(f"[Telegram] (offline) Alert: {signal}")
        return

    emoji = "🟢" if signal.get('direction') == 'LONG' else "🔴"
    msg = (
        f"{emoji} *{signal.get('direction', 'INFO')} Signal*\n"
        f"📊 Symbol: `{signal.get('symbol', 'N/A')}`\n"
        f"💰 Entry: `{signal.get('entry', 'N/A')}`\n"
        f"📝 Reason: {signal.get('reason', '')}\n"
    )
    if 'rsi' in signal:
        msg += f"📈 RSI: `{signal['rsi']:.1f}`\n"

    url = f"https://api.telegram.org/bot{token}/sendMessage"
    try:
        requests.post(url, json={
            'chat_id': chat_id,
            'text': msg,
            'parse_mode': 'Markdown',
        }, timeout=10)
    except Exception as e:
        print(f"[Telegram] Failed to send alert: {e}")
