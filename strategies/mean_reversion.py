import pandas as pd
import utils.indicators as ta
from strategies.base import BaseStrategy

class MeanReversion(BaseStrategy):
    """
    ALGO 03 — MEAN REVERSION (MR)
    Tier: SCALP / INTRADAY | Timeframe: 15m, 1h
    Focus: Trading over-extended moves back to the EMA 50.
    """
    
    NAME = "MEAN_REVERSION"
    TIER = "SCALP"
    REGIME_GATE = ['MEAN_REVERTING', 'CHOPPY_NOISE']
    
    def calculate_signal(self, df: pd.DataFrame, portfolio_value: float = 1000, **kwargs) -> dict:
        """
        Input: 15m or 1h OHLCV DataFrame
        """
        if len(df) < 50:
            return {'direction': 'NONE', 'reason': 'Insufficient data'}

        df = df.copy()
        # 1. Indicators
        df['rsi'] = ta.rsi(df['close'], length=14)
        bb = ta.bbands(df['close'], length=20, std=2)
        df['bb_lower'] = bb['BBL_20_2.0']
        df['bb_upper'] = bb['BBU_20_2.0']
        df['ema_50'] = ta.ema(df['close'], length=50)
        df['atr'] = ta.atr(df['high'], df['low'], df['close'], length=14)

        # Latest values
        price = df['close'].iloc[-1]
        rsi = df['rsi'].iloc[-1]
        bb_lower = df['bb_lower'].iloc[-1]
        bb_upper = df['bb_upper'].iloc[-1]
        ema_50 = df['ema_50'].iloc[-1]
        atr = df['atr'].iloc[-1]

        # 2. Logic: LONG (Oversold Extreme)
        if rsi < 30 and price < bb_lower:
            sl = price - (1.5 * atr)
            tp = ema_50 # TP at the mean
            
            # Risk/Reward Filter (handled by RiskManager later, but good here too)
            if (tp - price) < (price - sl): return {'direction': 'NONE', 'reason': 'Bad RR'}

            qty = self.calculate_position_size(portfolio_value, 1.0, price, sl)
            return {
                'direction': 'LONG',
                'entry': price,
                'sl': sl,
                'tp': tp,
                'qty': qty,
                'reason': f'MeanReversion: RSI={rsi:.1f} < 30 + BB Lower'
            }

        # 3. Logic: SHORT (Overbought Extreme)
        if rsi > 70 and price > bb_upper:
            sl = price + (1.5 * atr)
            tp = ema_50
            
            if (price - tp) < (sl - price): return {'direction': 'NONE', 'reason': 'Bad RR'}

            qty = self.calculate_position_size(portfolio_value, 1.0, price, sl)
            return {
                'direction': 'SHORT',
                'entry': price,
                'sl': sl,
                'tp': tp,
                'qty': qty,
                'reason': f'MeanReversion: RSI={rsi:.1f} > 70 + BB Upper'
            }

        return {'direction': 'NONE', 'reason': 'No MR extreme'}
