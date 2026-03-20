import pandas as pd
import utils.indicators as ta
import numpy as np

class FeatureProcessor:
    """
    Feature Machine.
    Generates 100+ engineered features for ML model training and inference.
    """
    
    def __init__(self):
        pass

    def add_all_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Adds technical, momentum, and volume features to the DataFrame.
        """
        df = df.copy()
        
        # 1. Price Features
        for n in [1, 3, 5, 10, 20]:
            df[f'log_return_{n}'] = np.log(df['close'] / df['close'].shift(n))
            
        # Candle Ratios
        df['high_low_range'] = df['high'] - df['low']
        df['body_ratio'] = abs(df['close'] - df['open']) / df['high_low_range']
        
        # 2. Technical Indicators (Multi-period)
        periods = [5, 10, 14, 20, 50, 100, 200]
        
        for p in periods:
            # RSI
            df[f'rsi_{p}'] = ta.rsi(df['close'], length=p)
            
            # BB Position
            bb = ta.bbands(df['close'], length=p, std=2)
            if bb is not None:
                df[f'bb_width_{p}'] = (bb[f'BBU_{p}_2.0'] - bb[f'BBL_{p}_2.0']) / bb[f'BBM_{p}_2.0']
                df[f'bb_pos_{p}'] = (df['close'] - bb[f'BBL_{p}_2.0']) / (bb[f'BBU_{p}_2.0'] - bb[f'BBL_{p}_2.0'])
                
            # EMA
            df[f'ema_{p}'] = ta.ema(df['close'], length=p)
            df[f'ema_dist_{p}'] = (df['close'] - df[f'ema_{p}']) / df['close']
        
        # 3. Momentum & Trend
        macd = ta.macd(df['close'])
        if macd is not None:
            df['macd_line'] = macd['MACD_12_26_9']
            df['macd_signal'] = macd['MACDs_12_26_9']
            df['macd_hist'] = macd['MACDh_12_26_9']
            
        adx_df = ta.adx(df['high'], df['low'], df['close'], length=14)
        if adx_df is not None:
            df['adx_14'] = adx_df['ADX_14']
            df['dmp_14'] = adx_df['DMP_14']
            df['dmn_14'] = adx_df['DMN_14']
            
        # 4. Volume Features
        df['obv'] = ta.obv(df['close'], df['volume'])
        
        # 5. Volatility
        df['atr_14'] = ta.atr(df['high'], df['low'], df['close'], length=14)
        
        return df.fillna(0)
