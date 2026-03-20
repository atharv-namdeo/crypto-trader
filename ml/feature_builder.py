"""
ml/feature_builder.py
Feature Vectorizer — Phase 3

Standardizes the dynamic feature dictionary into a fixed-size numpy array / PyTorch tensor.
Ensures the inference models always receive features in the exact same order as training.
"""

import numpy as np

# Total expected features: 35 explicit keys from feature_engine.py
FEATURE_KEYS = [
    # Price & Returns
    'log_return_1m', 'log_return_3m', 'log_return_5m', 'log_return_10m', 'log_return_20m', 'log_return_60m',
    'candle_body', 'upper_wick', 'lower_wick',
    
    # Trend
    'ema_9_dist', 'ema_21_dist', 'ema_50_dist', 'ema_200_dist',
    'adx_14', 'adx_pos_di', 'adx_neg_di', 'adx_slope_3',
    'macd_line', 'macd_signal', 'macd_histogram', 'macd_hist_slope',
    
    # Momentum
    'rsi_14_1h', 'rsi_7_1h', 'rsi_21_1h', 'rsi_14_1m',
    'stoch_k', 'stoch_d',
    
    # Volatility
    'bb_width', 'bb_position', 'bb_width_pct_90d',
    'realized_vol_14h', 'atr_14_1h', 'atr_14_1m',
    
    # Volume & Orderbook
    'volume_ratio', 'volume_zscore', 'cvd_1m', 'trade_imbalance',
    'ob_imbalance', 'spread_normalized', 'microprice_vs_mid',
    
    # VWAP
    'vwap_zscore'
]

def build_feature_vector(feature_dict: dict) -> np.ndarray:
    """
    Given a dictionary of features from feature_engine.py,
    returns a 1D numpy array of shape (len(FEATURE_KEYS),)
    NaNs and Infs are converted to 0.0.
    """
    vec = []
    for key in FEATURE_KEYS:
        val = feature_dict.get(key, 0.0)
        # Handle nan/inf
        if val is None or np.isnan(val) or np.isinf(val):
            val = 0.0
        vec.append(float(val))
    return np.array(vec, dtype=np.float32)

def get_feature_names():
    return FEATURE_KEYS
