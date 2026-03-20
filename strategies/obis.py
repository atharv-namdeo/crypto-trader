import pandas as pd
from strategies.base import BaseStrategy

class OrderBookImbalance(BaseStrategy):
    """
    ALGO 05 — ORDER BOOK IMBALANCE (OBIS)
    Tier: HFT / SCALP | Timeframe: Tick / 1m
    Focus: Scalping based on Bid/Ask pressure.
    """
    
    NAME = "OBIS"
    TIER = "SCALP"
    REGIME_GATE = ['MEAN_REVERTING', 'HIGH_VOLATILITY']
    
    def calculate_signal(self, df: pd.DataFrame, order_book: dict = None, portfolio_value: float = 1000, **kwargs) -> dict:
        """
        Input: 
            df (unused for OBIS)
            order_book: { 'bids': [[price, qty], ...], 'asks': [...] }
        """
        if order_book is None or not order_book.get('bids') or not order_book.get('asks'):
            return {'direction': 'NONE', 'reason': 'No order book data'}

        # 1. Calculate Imbalance (Top 10 Levels)
        bids = order_book['bids'][:10]
        asks = order_book['asks'][:10]
        
        bid_vol = sum([b[1] for b in bids])
        ask_vol = sum([a[1] for a in asks])
        
        if ask_vol == 0: return {'direction': 'NONE'}
        
        imbalance = bid_vol / ask_vol
        mid_price = (bids[0][0] + asks[0][0]) / 2

        # 2. Logic: LONG (Strong Bid Pressure)
        if imbalance > 1.8:
            sl = mid_price * 0.995 # 0.5% tight stop for scalping
            tp = mid_price * 1.01  # 1% TP
            qty = self.calculate_position_size(portfolio_value, 0.5, mid_price, sl)
            return {
                'direction': 'LONG',
                'entry': mid_price,
                'sl': sl,
                'tp': tp,
                'qty': qty,
                'reason': f'OBIS: Bid Pressure ({imbalance:.2f})'
            }

        # 3. Logic: SHORT (Strong Ask Pressure)
        if imbalance < 0.55:
            sl = mid_price * 1.005
            tp = mid_price * 0.99
            qty = self.calculate_position_size(portfolio_value, 0.5, mid_price, sl)
            return {
                'direction': 'SHORT',
                'entry': mid_price,
                'sl': sl,
                'tp': tp,
                'qty': qty,
                'reason': f'OBIS: Ask Pressure ({imbalance:.2f})'
            }

        return {'direction': 'NONE', 'reason': 'Order book balanced'}
