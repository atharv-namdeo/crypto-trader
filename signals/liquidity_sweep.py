import pandas as pd


def detect_liquidity_sweep(df, lookback=20):
    """
    Detects when price wicks through a recent high/low then closes back —
    classic stop hunt / liquidity grab.

    Returns a list of signal dicts with index, type, price, swept_level.
    """
    signals = []

    for i in range(lookback, len(df)):
        candle = df.iloc[i]
        prev_high = df['high'].iloc[i - lookback:i].max()
        prev_low = df['low'].iloc[i - lookback:i].min()

        # Bearish sweep: wick above recent high but closes below it
        if candle['high'] > prev_high and candle['close'] < prev_high:
            signals.append({
                'index': i,
                'type': 'bearish_sweep',
                'price': candle['close'],
                'swept_level': prev_high,
            })

        # Bullish sweep: wick below recent low but closes above it
        if candle['low'] < prev_low and candle['close'] > prev_low:
            signals.append({
                'index': i,
                'type': 'bullish_sweep',
                'price': candle['close'],
                'swept_level': prev_low,
            })

    return signals
