import os
from dotenv import load_dotenv

load_dotenv()

CAPITAL = float(os.getenv('CAPITAL', 1000))
RISK_PCT = float(os.getenv('RISK_PER_TRADE', 0.02))
MAX_DAILY_LOSS = 0.05  # 5% daily drawdown cap


def calculate_position_size(entry_price, stop_loss_price):
    """Position size based on fixed-% risk and distance to stop loss."""
    risk_amount = CAPITAL * RISK_PCT
    price_diff = abs(entry_price - stop_loss_price)
    if price_diff == 0:
        return 0
    qty = risk_amount / price_diff
    return round(qty, 4)


def get_stop_loss(entry, direction, atr):
    """ATR-based stop loss: 1.5× ATR from entry."""
    if direction == 'LONG':
        return entry - (1.5 * atr)
    return entry + (1.5 * atr)


def get_take_profit(entry, stop_loss, direction, rr=2.0):
    """Take profit at a given risk-reward ratio."""
    risk = abs(entry - stop_loss)
    if direction == 'LONG':
        return entry + (risk * rr)
    return entry - (risk * rr)


def check_daily_drawdown(starting_capital, current_capital):
    """Returns True if daily loss exceeds MAX_DAILY_LOSS threshold → stop trading."""
    loss_pct = (starting_capital - current_capital) / starting_capital
    return loss_pct >= MAX_DAILY_LOSS
