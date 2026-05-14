import numpy as np
import pandas as pd


def compute_volume_profile(df, num_bins=50):
    """
    Build a volume profile (price histogram weighted by volume).
    Returns a dict with:
        poc   – Point of Control (highest-volume price level)
        vah   – Value Area High
        val   – Value Area Low
        profile – full histogram as {price_level: volume}
    """
    price_min = df['low'].min()
    price_max = df['high'].max()
    bins = np.linspace(price_min, price_max, num_bins + 1)
    bin_centres = (bins[:-1] + bins[1:]) / 2

    vol_at_price = np.zeros(num_bins)
    for _, row in df.iterrows():
        # distribute the bar's volume across the bins it spans
        mask = (bin_centres >= row['low']) & (bin_centres <= row['high'])
        count = mask.sum()
        if count > 0:
            vol_at_price[mask] += row['volume'] / count

    poc_idx = np.argmax(vol_at_price)
    poc = float(bin_centres[poc_idx])

    # Value area = 70% of total volume centred on POC
    total_vol = vol_at_price.sum()
    target = total_vol * 0.70
    cumulative = 0.0
    lo, hi = poc_idx, poc_idx

    while cumulative < target and (lo > 0 or hi < num_bins - 1):
        expand_lo = vol_at_price[lo - 1] if lo > 0 else 0
        expand_hi = vol_at_price[hi + 1] if hi < num_bins - 1 else 0
        if expand_lo >= expand_hi and lo > 0:
            lo -= 1
            cumulative += expand_lo
        elif hi < num_bins - 1:
            hi += 1
            cumulative += expand_hi
        else:
            lo -= 1
            cumulative += expand_lo

    vah = float(bin_centres[hi])
    val = float(bin_centres[lo])

    profile = {float(bin_centres[i]): float(vol_at_price[i]) for i in range(num_bins)}

    return {'poc': poc, 'vah': vah, 'val': val, 'profile': profile}


def volume_profile_signal(df):
    """
    Returns bias based on where current price sits relative to the value area.
    """
    vp = compute_volume_profile(df)
    current = df['close'].iloc[-1]

    if current > vp['vah']:
        bias = 'bullish'
    elif current < vp['val']:
        bias = 'bearish'
    else:
        bias = 'neutral'

    return {
        'poc': vp['poc'],
        'vah': vp['vah'],
        'val': vp['val'],
        'price': current,
        'bias': bias,
    }
