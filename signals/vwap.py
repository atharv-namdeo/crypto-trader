import pandas as pd
import numpy as np


def calculate_anchored_vwap(df, anchor_index=0):
    """
    Anchored VWAP from a specific candle index.
    anchor_index = the bar to anchor from (e.g. swing high/low or day open).
    """
    sliced = df.iloc[anchor_index:].copy()
    sliced['tp'] = (sliced['high'] + sliced['low'] + sliced['close']) / 3
    sliced['tp_vol'] = sliced['tp'] * sliced['volume']
    sliced['cum_tp_vol'] = sliced['tp_vol'].cumsum()
    sliced['cum_vol'] = sliced['volume'].cumsum()
    sliced['avwap'] = sliced['cum_tp_vol'] / sliced['cum_vol']
    return sliced['avwap']


def vwap_signal(df):
    """Returns current price vs anchored VWAP bias (bullish / bearish)."""
    # Anchor to start of current day
    today_mask = df['timestamp'].dt.date == df['timestamp'].dt.date.iloc[-1]
    today_start = df[today_mask].index[0]
    anchor_idx = df.index.get_loc(today_start)

    avwap = calculate_anchored_vwap(df, anchor_idx)
    current_price = df['close'].iloc[-1]
    current_vwap = avwap.iloc[-1]

    return {
        'price': current_price,
        'vwap': current_vwap,
        'bias': 'bullish' if current_price > current_vwap else 'bearish',
    }
