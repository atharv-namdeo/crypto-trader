import pandas as pd
import numpy as np
import utils.indicators as ta
from strategies.base import BaseStrategy

class VolumeProfile(BaseStrategy):
    """
    ALGO 13 — VOLUME PROFILE (VPVR)
    Tier: INTRADAY / SWING | Timeframe: 1h, 4h
    Focus: Trading based on the Value Area (VAH/VAL) and Point of Control (POC).
    """
    
    NAME = "VOLUME_PROFILE"
    TIER = "INTRADAY"
    REGIME_GATE = ['TRENDING_BULL', 'TRENDING_BEAR', 'BREAKOUT_PENDING']
    
    def calculate_signal(self, df: pd.DataFrame, portfolio_value: float = 1000, **kwargs) -> dict:
        """
        Input: 1h or 4h OHLCV DataFrame
        """
        if len(df) < 100:
            return {'direction': 'NONE', 'reason': 'Insufficient data'}

        df_recent = df.tail(100).copy()
        
        # 1. Calculate Simple Volume Profile
        price_min = df_recent['low'].min()
        price_max = df_recent['high'].max()
        bins = np.linspace(price_min, price_max, 20)
        
        # Assign volume to bins based on (High + Low) / 2
        df_recent['bin'] = pd.cut((df_recent['high'] + df_recent['low']) / 2, bins=bins, labels=False)
        profile = df_recent.groupby('bin')['volume'].sum()
        
        if profile.empty: return {'direction': 'NONE'}
        
        # POC (Point of Control)
        poc_bin = profile.idxmax()
        poc_price = (bins[poc_bin] + bins[poc_bin+1]) / 2
        
        # Simple Value Area (Simplified 70% volume around POC)
        total_vol = profile.sum()
        target_vol = total_vol * 0.7
        
        accum_vol = profile.loc[poc_bin]
        l, r = poc_bin, poc_bin
        while accum_vol < target_vol:
            if l > 0 and r < len(profile) - 1:
                if profile.get(l-1, 0) > profile.get(r+1, 0):
                    l -= 1
                    accum_vol += profile[l]
                else:
                    r += 1
                    accum_vol += profile[r]
            elif l > 0:
                l -= 1
                accum_vol += profile[l]
            elif r < len(profile) - 1:
                r += 1
                accum_vol += profile[r]
            else:
                break
        
        val = bins[l]
        vah = bins[r+1]
        
        price = df['close'].iloc[-1]
        atr = ta.atr(df['high'], df['low'], df['close'], length=14).iloc[-1]

        # 2. Logic: LONG (Breakout above VAH)
        if price > vah:
            sl = vah - (0.5 * atr)
            tp = price + (3.0 * atr)
            qty = self.calculate_position_size(portfolio_value, 1.0, price, sl)
            return {
                'direction': 'LONG',
                'entry': price,
                'sl': sl,
                'tp': tp,
                'qty': qty,
                'reason': f'Volume Profile: Breakout above VAH ({vah:.2f})'
            }

        # 3. Logic: SHORT (Breakout below VAL)
        if price < val:
            sl = val + (0.5 * atr)
            tp = price - (3.0 * atr)
            qty = self.calculate_position_size(portfolio_value, 1.0, price, sl)
            return {
                'direction': 'SHORT',
                'entry': price,
                'sl': sl,
                'tp': tp,
                'qty': qty,
                'reason': f'Volume Profile: Breakout below VAL ({val:.2f})'
            }

        return {'direction': 'NONE', 'reason': 'Price within Value Area'}
