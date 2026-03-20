import utils.indicators as ta


def macd_signal(df, fast=12, slow=26, signal=9):
    """
    MACD crossover filter.
    Returns dict with macd, signal line, histogram, and bullish/bearish bias.
    """
    macd = ta.macd(df['close'], fast=fast, slow=slow, signal=signal)
    macd_line = macd[f'MACD_{fast}_{slow}_{signal}'].iloc[-1]
    signal_line = macd[f'MACDs_{fast}_{slow}_{signal}'].iloc[-1]
    hist = macd[f'MACDh_{fast}_{slow}_{signal}'].iloc[-1]

    return {
        'macd': macd_line,
        'signal': signal_line,
        'histogram': hist,
        'bias': 'bullish' if macd_line > signal_line else 'bearish',
    }
