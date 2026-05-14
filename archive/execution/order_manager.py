from config import get_exchange
from utils.firebase_client import log_trade
from utils.telegram_alert import send_alert

exchange = get_exchange()


def place_order(signal, stop_loss, take_profit, qty):
    """
    Place a bracket order: market entry + stop-loss + take-profit.
    Logs the trade and sends a Telegram alert.
    """
    try:
        side = 'buy' if signal['direction'] == 'LONG' else 'sell'
        close_side = 'sell' if signal['direction'] == 'LONG' else 'buy'

        # Market entry
        order = exchange.create_order(
            symbol=signal['symbol'],
            type='market',
            side=side,
            amount=qty,
        )

        # Stop loss
        exchange.create_order(
            symbol=signal['symbol'],
            type='STOP_MARKET',
            side=close_side,
            amount=qty,
            params={'stopPrice': stop_loss, 'reduceOnly': True},
        )

        # Take profit
        exchange.create_order(
            symbol=signal['symbol'],
            type='TAKE_PROFIT_MARKET',
            side=close_side,
            amount=qty,
            params={'stopPrice': take_profit, 'reduceOnly': True},
        )

        trade_data = {
            **signal,
            'qty': qty,
            'sl': stop_loss,
            'tp': take_profit,
            'order_id': order['id'],
        }
        log_trade(trade_data)
        send_alert({
            **signal,
            'reason': f"✅ Order placed | SL:{stop_loss:.2f} TP:{take_profit:.2f} Qty:{qty}",
        })

        return order

    except Exception as e:
        print(f"[OrderManager] Order failed: {e}")
        send_alert({
            'symbol': signal.get('symbol', '?'),
            'direction': signal.get('direction', '?'),
            'entry': signal.get('entry', '?'),
            'reason': f"❌ Order FAILED: {e}",
        })
        return None
