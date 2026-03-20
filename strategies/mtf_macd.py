import pandas as pd
import utils.indicators as ta
from strategies.base import BaseStrategy

class MTFMACD(BaseStrategy):
    """
    ALGO 08 — MACD MULTI-TIMEFRAME (MTF-MACD)
    Tier: INTRADAY / SWING | Timeframe: 1h, 4h
    Focus: High-confluence momentum signals filtered by macro trend.
    """
    
    NAME = "MTF_MACD"
    TIER = "INTRADAY"
    REGIME_GATE = ['TRENDING_BULL', 'TRENDING_BEAR', 'BREAKOUT_PENDING']
    
    def calculate_signal(self, df_1h: pd.DataFrame, df_4h: pd.DataFrame = None, portfolio_value: float = 1000, **kwargs) -> dict:
        """
        Input: 
            df_1h: 1h OHLCV DataFrame
            df_4h: 4h OHLCV DataFrame (Macro context)
        """
        if df_1h is None or df_4h is None or len(df_1h) < 50 or len(df_4h) < 50:
            return {'direction': 'NONE', 'reason': 'Missing timeframe data'}

        # 1. 4h Macro Momentum
        macd_4h = ta.macd(df_4h['close'])
        macro_line = macd_4h['MACD_12_26_9'].iloc[-1]
        
        # 2. 1h Execution Momentum
        macd_1h = ta.macd(df_1h['close'])
        hist = macd_1h['MACDh_12_26_9'].iloc[-1]
        prev_hist = macd_1h['MACDh_12_26_9'].iloc[-2]
        
        price = df_1h['close'].iloc[-1]
        atr = ta.atr(df_1h['high'], df_1h['low'], df_1h['close'], length=14).iloc[-1]

        # 3. Logic: LONG
        # Condition: 4h MACD > 0 (Bullish Macro) + 1h Histogram crosses above 0
        if macro_line > 0 and hist > 0 and prev_hist <= 0:
            sl = price - (1.5 * atr)
            tp = price + (3.0 * atr)
            qty = self.calculate_position_size(portfolio_value, 1.0, price, sl)
            return {
                'direction': 'LONG',
                'entry': price,
                'sl': sl,
                'tp': tp,
                'qty': qty,
                'reason': 'MTF-MACD: Bullish Macro (4h) + Bullish Hist Cross (1h)'
            }

        # 4. Logic: SHORT
        # Condition: 4h MACD < 0 (Bearish Macro) + 1h Histogram crosses below 0
        if macro_line < 0 and hist < 0 and prev_hist >= 0:
            sl = price + (1.5 * atr)
            tp = price - (3.0 * atr)
            qty = self.calculate_position_size(portfolio_value, 1.0, price, sl)
            return {
                'direction': 'SHORT',
                'entry': price,
                'sl': sl,
                'tp': tp,
                'qty': qty,
                'reason': 'MTF-MACD: Bearish Macro (4h) + Bearish Hist Cross (1h)'
            }

        return {'direction': 'NONE', 'reason': 'No MACD confluence'}
