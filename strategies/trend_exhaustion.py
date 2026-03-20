import pandas as pd
import utils.indicators as ta
from strategies.base import BaseStrategy

class TrendExhaustion(BaseStrategy):
    """
    ALGO 20 — TREND EXHAUSTION (CLIMAX REVERSAL)
    Tier: INTRADAY / SWING | Timeframe: 1h, 4h
    Focus: Detecting the end of a trend via volume climax + momentum divergence.
    """
    
    NAME = "TREND_EXHAUST"
    TIER = "INTRADAY"
    REGIME_GATE = ['TRENDING_BULL', 'TRENDING_BEAR', 'HIGH_VOLATILITY']
    
    def calculate_signal(self, df: pd.DataFrame, portfolio_value: float = 1000, **kwargs) -> dict:
        if len(df) < 60:
            return {'direction': 'NONE', 'reason': 'Insufficient data'}

        df = df.copy()
        df['rsi'] = ta.rsi(df['close'], length=14)
        df['atr'] = ta.atr(df['high'], df['low'], df['close'], length=14)
        df['vol_ma'] = df['volume'].rolling(window=20).mean()
        
        price = df['close'].iloc[-1]
        rsi = df['rsi'].iloc[-1]
        vol = df['volume'].iloc[-1]
        vol_ma = df['vol_ma'].iloc[-1]
        atr = df['atr'].iloc[-1]
        
        # Volume Climax: Current Volume > 2.5x Average
        vol_climax = vol > 2.5 * vol_ma
        
        # 1. Logic: Bearish Exhaustion (Uptrend ending)
        # High RSI + Volume Climax + Bearish candle
        bearish_candle = df['close'].iloc[-1] < df['open'].iloc[-1]
        if rsi > 75 and vol_climax and bearish_candle:
            sl = price + (2.0 * atr)
            tp = price - (4.0 * atr)
            qty = self.calculate_position_size(portfolio_value, 1.0, price, sl)
            return {
                'direction': 'SHORT', 'entry': price, 'sl': sl, 'tp': tp,
                'qty': qty, 'reason': f'Trend Exhaustion: Bearish Climax (RSI={rsi:.1f}, Vol={vol/vol_ma:.1f}x)'
            }

        # 2. Logic: Bullish Exhaustion (Downtrend ending)
        bullish_candle = df['close'].iloc[-1] > df['open'].iloc[-1]
        if rsi < 25 and vol_climax and bullish_candle:
            sl = price - (2.0 * atr)
            tp = price + (4.0 * atr)
            qty = self.calculate_position_size(portfolio_value, 1.0, price, sl)
            return {
                'direction': 'LONG', 'entry': price, 'sl': sl, 'tp': tp,
                'qty': qty, 'reason': f'Trend Exhaustion: Bullish Climax (RSI={rsi:.1f}, Vol={vol/vol_ma:.1f}x)'
            }

        return {'direction': 'NONE', 'reason': 'No exhaustion signal'}
