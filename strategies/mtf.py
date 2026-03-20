import pandas as pd
import utils.indicators as ta
from strategies.base import BaseStrategy

class MomentumTrendFollowing(BaseStrategy):
    """
    ALGO 01 — MOMENTUM TREND FOLLOWING (MTF)
    Tier: INTRADAY / SWING | Timeframe: 1h, 4h
    """
    
    NAME = "MTF"
    TIER = "INTRADAY"
    REGIME_GATE = ['TRENDING_BULL', 'TRENDING_BEAR']
    
    def calculate_signal(self, df: pd.DataFrame, macro_trend: str = 'NEUTRAL', portfolio_value: float = 1000) -> dict:
        """
        Input: 
            df (1h OHLCV DataFrame)
            macro_trend (from 4h EMA 200)
            portfolio_value (for position sizing)
        """
        if len(df) < 50:
            return {'symbol': None, 'direction': 'NONE', 'reason': 'Insufficient data'}

        df = df.copy()
        # 1. Indicators
        df['ema_9'] = ta.ema(df['close'], length=9)
        df['ema_21'] = ta.ema(df['close'], length=21)
        adx_df = ta.adx(df['high'], df['low'], df['close'], length=14)
        df['adx'] = adx_df['ADX_14']
        df['atr'] = ta.atr(df['high'], df['low'], df['close'], length=14)
        df['rsi'] = ta.rsi(df['close'], length=14)
        df['vol_sma'] = df['volume'].rolling(20).mean()

        # Latest values
        price = df['close'].iloc[-1]
        ema_9 = df['ema_9'].iloc[-1]
        ema_21 = df['ema_21'].iloc[-1]
        prev_ema_9 = df['ema_9'].iloc[-2]
        prev_ema_21 = df['ema_21'].iloc[-2]
        adx = df['adx'].iloc[-1]
        atr = df['atr'].iloc[-1]
        rsi = df['rsi'].iloc[-1]
        volume = df['volume'].iloc[-1]
        vol_sma = df['vol_sma'].iloc[-1]

        # 2. Crossovers
        bullish_cross = prev_ema_9 <= prev_ema_21 and ema_9 > ema_21
        bearish_cross = prev_ema_9 >= prev_ema_21 and ema_9 < ema_21

        # 3. Entry Logic: LONG
        if bullish_cross and macro_trend == 'BULLISH' and adx > 25:
            if volume > 1.5 * vol_sma and 50 < rsi < 70:
                sl = price - (1.5 * atr)
                tp = price + (3.0 * atr) # 2:1 RR
                qty = self.calculate_position_size(portfolio_value, 1.0, price, sl)
                return {
                    'direction': 'LONG',
                    'entry': price,
                    'sl': sl,
                    'tp': tp,
                    'qty': qty,
                    'reason': 'MTF Bullish Cross + Macro Confluence'
                }

        # 4. Entry Logic: SHORT
        if bearish_cross and macro_trend == 'BEARISH' and adx > 25:
            if volume > 1.5 * vol_sma and 30 < rsi < 50:
                sl = price + (1.5 * atr)
                tp = price - (3.0 * atr)
                qty = self.calculate_position_size(portfolio_value, 1.0, price, sl)
                return {
                    'direction': 'SHORT',
                    'entry': price,
                    'sl': sl,
                    'tp': tp,
                    'qty': qty,
                    'reason': 'MTF Bearish Cross + Macro Confluence'
                }

        return {'direction': 'NONE', 'reason': 'No MTF signal'}
