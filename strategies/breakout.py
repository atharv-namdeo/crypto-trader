import pandas as pd
import utils.indicators as ta
from strategies.base import BaseStrategy

class VolatilityBreakout(BaseStrategy):
    """
    ALGO 04 — VOLATILITY BREAKOUT (BOLINGER SQUEEZE)
    Tier: SCALP / INTRADAY | Timeframe: 15m, 1h
    Focus: Capturing explosive moves after high-compression periods.
    """
    
    NAME = "BREAKOUT"
    TIER = "INTRADAY"
    REGIME_GATE = ['BREAKOUT_PENDING', 'TRENDING_BULL', 'TRENDING_BEAR']
    
    def calculate_signal(self, df: pd.DataFrame, portfolio_value: float = 1000, **kwargs) -> dict:
        """
        Input: 15m or 1h OHLCV DataFrame
        """
        if len(df) < 50:
            return {'direction': 'NONE', 'reason': 'Insufficient data'}

        df = df.copy()
        # 1. Indicators
        bb = ta.bbands(df['close'], length=20, std=2)
        kc = ta.keltner_channels(df['high'], df['low'], df['close'], length=20, mult=1.5)
        
        df['bb_lower'] = bb['BBL_20_2.0']
        df['bb_upper'] = bb['BBU_20_2.0']
        df['kc_lower'] = kc['KCL_20_1.5']
        df['kc_upper'] = kc['KCU_20_1.5']
        df['atr'] = ta.atr(df['high'], df['low'], df['close'], length=14)

        # 2. Squeeze Detection
        # Squeeze = Bollinger Bands inside Keltner Channels
        df['squeeze'] = (df['bb_upper'] < df['kc_upper']) & (df['bb_lower'] > df['kc_lower'])
        
        # Latest values
        price = df['close'].iloc[-1]
        prev_price = df['close'].iloc[-2]
        bb_upper = df['bb_upper'].iloc[-1]
        bb_lower = df['bb_lower'].iloc[-1]
        is_squeezed = df['squeeze'].iloc[-1]
        atr = df['atr'].iloc[-1]

        # 3. Logic: LONG Breakout
        if is_squeezed and price > bb_upper and prev_price <= df['bb_upper'].iloc[-2]:
            sl = price - (2.0 * atr)
            tp = price + (4.0 * atr) # 2:1 RR
            qty = self.calculate_position_size(portfolio_value, 1.0, price, sl)
            return {
                'direction': 'LONG',
                'entry': price,
                'sl': sl,
                'tp': tp,
                'qty': qty,
                'reason': 'Volatility Squeeze + Bullish Breakout'
            }

        # 4. Logic: SHORT Breakout
        if is_squeezed and price < bb_lower and prev_price >= df['bb_lower'].iloc[-2]:
            sl = price + (2.0 * atr)
            tp = price - (4.0 * atr)
            qty = self.calculate_position_size(portfolio_value, 1.0, price, sl)
            return {
                'direction': 'SHORT',
                'entry': price,
                'sl': sl,
                'tp': tp,
                'qty': qty,
                'reason': 'Volatility Squeeze + Bearish Breakout'
            }

        return {'direction': 'NONE', 'reason': 'No breakout squeeze'}
