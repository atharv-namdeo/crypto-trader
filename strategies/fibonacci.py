import pandas as pd
import utils.indicators as ta
from strategies.base import BaseStrategy

class FibonacciRetracement(BaseStrategy):
    """
    ALGO 10 — FIBONACCI RETRACEMENT
    Tier: INTRADAY / SWING | Timeframe: 1h, 4h
    Focus: Buying the dip at high-confluence 0.618/0.786 Fibonacci levels.
    """
    
    NAME = "FIBONACCI"
    TIER = "INTRADAY"
    REGIME_GATE = ['TRENDING_BULL', 'TRENDING_BEAR', 'BREAKOUT_PENDING']
    
    def calculate_signal(self, df: pd.DataFrame, portfolio_value: float = 1000, **kwargs) -> dict:
        """
        Input: 1h or 4h OHLCV DataFrame
        """
        if len(df) < 100:
            return {'direction': 'NONE', 'reason': 'Insufficient data'}

        df = df.copy()
        # 1. Detect Major Swing (100 period)
        start_price = df['low'].rolling(100).min().iloc[-1]
        end_price = df['high'].rolling(100).max().iloc[-1]
        current_price = df['close'].iloc[-1]
        
        # Determine Trend direction for the swing
        is_bullish_swing = df['high'].idxmax() > df['low'].idxmin()
        diff = end_price - start_price
        
        if diff == 0: return {'direction': 'NONE'}

        # 2. Fibonacci Levels
        fib_618 = end_price - (0.382 * diff) if is_bullish_swing else start_price + (0.382 * diff)
        fib_786 = end_price - (0.214 * diff) if is_bullish_swing else start_price + (0.214 * diff)
        
        # 3. Logic: BULLISH Retracement (Buy the Dip)
        if is_bullish_swing and current_price <= fib_618 and current_price > fib_786:
            # Confluence check: RSI oversold or near lower BB/EMA
            df['ema_50'] = ta.ema(df['close'], length=50)
            ema_50 = df['ema_50'].iloc[-1]
            
            if current_price < ema_50: # Below mean entry
                sl = start_price - (0.02 * start_price) # 2% below the swing low
                tp = end_price
                qty = self.calculate_position_size(portfolio_value, 1.0, current_price, sl)
                return {
                    'direction': 'LONG',
                    'entry': current_price,
                    'sl': sl,
                    'tp': tp,
                    'qty': qty,
                    'reason': f'Fibonacci: Bullish Retracement at 0.618 level ({fib_618:.2f})'
                }

        # 4. Logic: BEARISH Retracement (Sell the Rip)
        if not is_bullish_swing and current_price >= fib_618 and current_price < fib_786:
            df['ema_50'] = ta.ema(df['close'], length=50)
            ema_50 = df['ema_50'].iloc[-1]
            
            if current_price > ema_50:
                sl = start_price + (0.02 * start_price)
                tp = end_price
                qty = self.calculate_position_size(portfolio_value, 1.0, current_price, sl)
                return {
                    'direction': 'SHORT',
                    'entry': current_price,
                    'sl': sl,
                    'tp': tp,
                    'qty': qty,
                    'reason': f'Fibonacci: Bearish Retracement at 0.618 level ({fib_618:.2f})'
                }

        return {'direction': 'NONE', 'reason': 'Price not in Fib range'}
