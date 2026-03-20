import pandas as pd
import utils.indicators as ta

class RegimeClassifier:
    """
    Global Regime Classifier based on Top 20 Algorithms Specification.
    Determines market state (TRENDING, MEAN_REVERTING, etc.) to activate specific algos.
    """
    
    STATES = [
        'TRENDING_BULL',
        'TRENDING_BEAR',
        'MEAN_REVERTING',
        'HIGH_VOLATILITY',
        'BREAKOUT_PENDING',
        'CHOPPY_NOISE'
    ]

    def __init__(self):
        pass

    def classify(self, df: pd.DataFrame, funding_rate: float = 0.0) -> dict:
        """
        Classifies the current market regime.
        df: OHLCV DataFrame with at least 200 periods.
        """
        if len(df) < 200:
            return {'regime': 'CHOPPY_NOISE', 'confidence': 0.1}

        df = df.copy()
        # 1. Features Calculation
        adx_df = ta.adx(df['high'], df['low'], df['close'], length=14)
        df['adx'] = adx_df['ADX_14']
        df['ema_50'] = ta.ema(df['close'], length=50)
        df['rsi'] = ta.rsi(df['close'], length=14)
        
        # Bollinger Bands for volatility
        bb = ta.bbands(df['close'], length=20, std=2)
        df['bb_width'] = (bb['BBU_20_2.0'] - bb['BBL_20_2.0']) / bb['BBM_20_2.0']
        df['bb_width_sma'] = df['bb_width'].rolling(20).mean()
        
        # Realized Volatility (1h)
        df['returns'] = df['close'].pct_change()
        df['realized_vol'] = df['returns'].rolling(60).std()
        df['avg_vol'] = df['realized_vol'].rolling(200).mean()

        # Latest values
        adx = df['adx'].iloc[-1]
        price = df['close'].iloc[-1]
        ema_50 = df['ema_50'].iloc[-1]
        rsi = df['rsi'].iloc[-1]
        bb_width = df['bb_width'].iloc[-1]
        bb_width_sma = df['bb_width_sma'].iloc[-1]
        realized_vol = df['realized_vol'].iloc[-1]
        avg_vol = df['avg_vol'].iloc[-1]

        # 2. Logic Gates (Priority Order)
        
        # HIGH_VOLATILITY
        if realized_vol > 2 * avg_vol or bb_width > 2 * bb_width_sma:
            return {'regime': 'HIGH_VOLATILITY', 'confidence': 0.9}

        # BREAKOUT_PENDING (Volatility Compression)
        bb_width_10th = df['bb_width'].rolling(500).quantile(0.10).iloc[-1]
        if bb_width < bb_width_10th:
            return {'regime': 'BREAKOUT_PENDING', 'confidence': 0.85}

        # TRENDING_BULL
        if adx > 25 and price > ema_50 and rsi > 55 and funding_rate > 0:
            return {'regime': 'TRENDING_BULL', 'confidence': 0.8}
            
        # TRENDING_BEAR
        if adx > 25 and price < ema_50 and rsi < 45 and funding_rate < 0:
            return {'regime': 'TRENDING_BEAR', 'confidence': 0.8}

        # CHOPPY_NOISE
        if adx < 15:
            return {'regime': 'CHOPPY_NOISE', 'confidence': 0.75}

        # MEAN_REVERTING
        if adx < 20 and bb_width < bb_width_sma and abs(rsi - 50) < 15:
            return {'regime': 'MEAN_REVERTING', 'confidence': 0.7}

        # Fallback
        return {'regime': 'CHOPPY_NOISE', 'confidence': 0.5}
