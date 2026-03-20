import pandas as pd
import utils.indicators as ta
from strategies.base import BaseStrategy

class GANNFan(BaseStrategy):
    """
    ALGO 17 — GANN FAN (ANGLE-BASED S/R)
    Tier: SWING | Timeframe: 4h, 1D
    Focus: Price-time geometry using GANN angles for dynamic S/R.
    """
    
    NAME = "GANN_FAN"
    TIER = "SWING"
    REGIME_GATE = ['TRENDING_BULL', 'TRENDING_BEAR']
    
    def calculate_signal(self, df: pd.DataFrame, portfolio_value: float = 1000, **kwargs) -> dict:
        if len(df) < 100:
            return {'direction': 'NONE', 'reason': 'Insufficient data'}

        df = df.copy()
        # 1. Determine Major Swing
        swing_low_idx = df['low'].rolling(100).apply(lambda x: x.argmin(), raw=True).iloc[-1]
        swing_high_idx = df['high'].rolling(100).apply(lambda x: x.argmax(), raw=True).iloc[-1]
        
        swing_low = df['low'].iloc[-100:].min()
        swing_high = df['high'].iloc[-100:].max()
        price_range = swing_high - swing_low
        
        if price_range == 0: return {'direction': 'NONE'}
        
        price = df['close'].iloc[-1]
        atr = ta.atr(df['high'], df['low'], df['close'], length=14).iloc[-1]
        
        # 2. GANN Levels (1x1 = 45deg, simplified as % retracements)
        gann_1x1 = swing_low + (price_range * 0.50)  # 50% angle
        gann_1x2 = swing_low + (price_range * 0.25)  # 25% angle
        gann_2x1 = swing_low + (price_range * 0.75)  # 75% angle
        
        # 3. Logic: LONG (Price bounces off 1x2 support)
        if price <= gann_1x2 * 1.01 and price >= gann_1x2 * 0.99:
            sl = swing_low - (0.5 * atr)
            tp = gann_1x1
            qty = self.calculate_position_size(portfolio_value, 1.0, price, sl)
            return {
                'direction': 'LONG', 'entry': price, 'sl': sl, 'tp': tp,
                'qty': qty, 'reason': f'GANN: Bounce from 1x2 ({gann_1x2:.2f})'
            }

        # 4. Logic: SHORT (Price rejects 2x1 resistance)
        if price >= gann_2x1 * 0.99 and price <= gann_2x1 * 1.01:
            sl = swing_high + (0.5 * atr)
            tp = gann_1x1
            qty = self.calculate_position_size(portfolio_value, 1.0, price, sl)
            return {
                'direction': 'SHORT', 'entry': price, 'sl': sl, 'tp': tp,
                'qty': qty, 'reason': f'GANN: Reject from 2x1 ({gann_2x1:.2f})'
            }

        return {'direction': 'NONE', 'reason': 'Not at GANN level'}
