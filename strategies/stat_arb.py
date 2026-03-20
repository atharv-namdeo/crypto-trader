import pandas as pd
import numpy as np
import utils.indicators as ta
from strategies.base import BaseStrategy

class StatArb(BaseStrategy):
    """
    ALGO 02 — STATISTICAL ARBITRAGE (BTC/ETH)
    Tier: SCALP / INTRADAY | Timeframe: 15m, 1h
    Focus: Mean reversion of the ETH/BTC ratio.
    """
    
    NAME = "STAT_ARB"
    TIER = "INTRADAY"
    REGIME_GATE = ['MEAN_REVERTING', 'CHOPPY_NOISE']
    
    def calculate_signal(self, df_dict: dict, portfolio_value: float = 1000, **kwargs) -> dict:
        """
        Input: 
            df_dict: { 'BTC/USDT': df, 'ETH/USDT': df }
        """
        btc_df = df_dict.get('BTC/USDT')
        eth_df = df_dict.get('ETH/USDT')
        
        if btc_df is None or eth_df is None or len(btc_df) < 60:
            return {'direction': 'NONE', 'reason': 'Missing pair data'}

        # Ensure indexes align
        common_idx = btc_df.index.intersection(eth_df.index)
        btc = btc_df.loc[common_idx, 'close']
        eth = eth_df.loc[common_idx, 'close']

        # 1. Ratio & Z-Score
        ratio = eth / btc
        ratio_ma = ratio.rolling(window=20).mean()
        ratio_std = ratio.rolling(window=20).std()
        z_score = (ratio - ratio_ma) / ratio_std
        
        # 2. Correlation Filter (Safety)
        correlation = eth.rolling(60).corr(btc)
        
        # Latest values
        curr_z = z_score.iloc[-1]
        curr_corr = correlation.iloc[-1]
        curr_eth_price = eth.iloc[-1]
        
        # 3. Entry Logic (Trading ETH against BTC)
        if curr_corr > 0.85:
            # ETH is undervalued relative to BTC
            if curr_z < -2.0:
                sl = curr_eth_price * 0.97 # 3% SL
                tp = curr_eth_price * 1.05 # 5% TP
                qty = self.calculate_position_size(portfolio_value, 1.0, curr_eth_price, sl)
                return {
                    'symbol': 'ETH/USDT',
                    'direction': 'LONG',
                    'entry': curr_eth_price,
                    'sl': sl,
                    'tp': tp,
                    'qty': qty,
                    'reason': f'StatArb: ETH Undervalued (Z={curr_z:.2f})'
                }
            
            # ETH is overvalued relative to BTC
            if curr_z > 2.0:
                sl = curr_eth_price * 1.03
                tp = curr_eth_price * 0.95
                qty = self.calculate_position_size(portfolio_value, 1.0, curr_eth_price, sl)
                return {
                    'symbol': 'ETH/USDT',
                    'direction': 'SHORT',
                    'entry': curr_eth_price,
                    'sl': sl,
                    'tp': tp,
                    'qty': qty,
                    'reason': f'StatArb: ETH Overvalued (Z={curr_z:.2f})'
                }

        return {'direction': 'NONE', 'reason': 'No StatArb divergence'}
