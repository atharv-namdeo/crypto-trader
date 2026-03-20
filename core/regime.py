import pandas as pd
import numpy as np
import utils.indicators as ta


class RegimeClassifier:
    """
    Softened Regime Classifier — confidence-weighted, no hard funding_rate gate.
    Returns label + confidence score (0–1) for ensemble weighting.
    """

    STATES = [
        'TRENDING_BULL',
        'TRENDING_BEAR',
        'MEAN_REVERTING',
        'HIGH_VOLATILITY',
        'BREAKOUT_PENDING',
        'CHOPPY_NOISE',
    ]

    def __init__(self):
        pass

    def classify(self, df: pd.DataFrame, funding_rate: float = 0.0) -> dict:
        """
        Classifies the current market regime with soft confidence scoring.
        df: OHLCV DataFrame with at least 50 periods (was 200 — now more lenient).
        """
        if len(df) < 50:
            return {'regime': 'CHOPPY_NOISE', 'confidence': 0.3}

        df = df.copy()

        # ── Features ──────────────────────────────────────────────────────
        adx_df = ta.adx(df['high'], df['low'], df['close'], length=14)
        df['adx'] = adx_df['ADX_14']
        df['ema_50'] = ta.ema(df['close'], length=50)
        df['rsi'] = ta.rsi(df['close'], length=14)

        bb = ta.bbands(df['close'], length=20, std=2)
        df['bb_width'] = (bb['BBU_20_2.0'] - bb['BBL_20_2.0']) / bb['BBM_20_2.0']
        df['bb_width_sma'] = df['bb_width'].rolling(20).mean()

        df['returns'] = df['close'].pct_change()
        df['realized_vol'] = df['returns'].rolling(20).std()
        df['avg_vol'] = df['realized_vol'].rolling(min(100, len(df))).mean()

        adx = float(df['adx'].iloc[-1]) if not np.isnan(df['adx'].iloc[-1]) else 20.0
        price = float(df['close'].iloc[-1])
        ema_50 = float(df['ema_50'].iloc[-1])
        rsi = float(df['rsi'].iloc[-1]) if not np.isnan(df['rsi'].iloc[-1]) else 50.0
        bb_width = float(df['bb_width'].iloc[-1])
        bb_width_sma = float(df['bb_width_sma'].iloc[-1]) if not np.isnan(df['bb_width_sma'].iloc[-1]) else bb_width
        realized_vol = float(df['realized_vol'].iloc[-1]) if not np.isnan(df['realized_vol'].iloc[-1]) else 0.01
        avg_vol = float(df['avg_vol'].iloc[-1]) if not np.isnan(df['avg_vol'].iloc[-1]) else 0.01

        # ── Collect candidate scores ──────────────────────────────────────
        scores = {}

        # HIGH_VOLATILITY — vol spike or BB explosion
        vol_ratio = realized_vol / (avg_vol + 1e-9)
        bb_ratio = bb_width / (bb_width_sma + 1e-9)
        hv_score = min(max((vol_ratio - 1.5) / 1.0, 0), 1.0) * 0.6 + \
                   min(max((bb_ratio - 1.5) / 1.0, 0), 1.0) * 0.4
        scores['HIGH_VOLATILITY'] = hv_score

        # BREAKOUT_PENDING — squeeze (BB very narrow vs history)
        bb_history = df['bb_width'].dropna()
        if len(bb_history) >= 20:
            pct10 = float(np.percentile(bb_history, 10))
            squeeze_score = max(0.0, 1.0 - (bb_width / (pct10 + 1e-9) - 1.0))
            scores['BREAKOUT_PENDING'] = float(np.clip(squeeze_score, 0, 1))
        else:
            scores['BREAKOUT_PENDING'] = 0.0

        # TRENDING_BULL — ADX strength + price above EMA + RSI bullish
        # REMOVED: funding_rate hard requirement (was blocking all bull signals)
        tb_adx = np.clip((adx - 20) / 20, 0, 1)           # 0 at ADX=20, 1 at ADX=40
        tb_ema = 1.0 if price > ema_50 else 0.0
        tb_rsi = np.clip((rsi - 50) / 30, 0, 1)            # 0 at RSI=50, 1 at RSI=80
        tb_fund = np.clip(funding_rate / 0.001 + 0.5, 0, 1) # mild positive weight
        scores['TRENDING_BULL'] = float(tb_adx * 0.4 + tb_ema * 0.3 +
                                        tb_rsi * 0.2 + tb_fund * 0.1)

        # TRENDING_BEAR — ADX + price below EMA + RSI bearish
        bear_adx = np.clip((adx - 20) / 20, 0, 1)
        bear_ema = 1.0 if price < ema_50 else 0.0
        bear_rsi = np.clip((50 - rsi) / 30, 0, 1)
        bear_fund = np.clip(-funding_rate / 0.001 + 0.5, 0, 1)
        scores['TRENDING_BEAR'] = float(bear_adx * 0.4 + bear_ema * 0.3 +
                                        bear_rsi * 0.2 + bear_fund * 0.1)

        # MEAN_REVERTING — low ADX + BB narrow + RSI mid
        mr_adx = np.clip(1.0 - (adx - 10) / 20, 0, 1)     # 1 at ADX=10, 0 at ADX=30
        mr_bb = np.clip(1.0 - (bb_width / (bb_width_sma + 1e-9) - 0.5) / 0.5, 0, 1)
        mr_rsi = np.clip(1.0 - abs(rsi - 50) / 25, 0, 1)   # 1 at RSI=50, 0 at RSI=25/75
        scores['MEAN_REVERTING'] = float(mr_adx * 0.4 + mr_bb * 0.3 + mr_rsi * 0.3)

        # CHOPPY_NOISE — weak ADX, no clear structure
        choppy_adx = np.clip(1.0 - (adx - 10) / 10, 0, 1)  # 1 at ADX=10, 0 at ADX=20
        scores['CHOPPY_NOISE'] = float(choppy_adx * 0.5 + (1 - max(scores.values())) * 0.5)

        # ── Winner = highest score ────────────────────────────────────────
        best_regime = max(scores, key=scores.get)
        best_conf = scores[best_regime]

        # Minimum confidence floor — always return SOMETHING actionable
        # Old: fell through to CHOPPY_NOISE → 0 strategies activated
        # New: fall through to MEAN_REVERTING at 0.4 confidence
        if best_conf < 0.25:
            return {'regime': 'MEAN_REVERTING', 'confidence': 0.4, 'scores': scores}

        return {
            'regime': best_regime,
            'confidence': float(np.clip(best_conf, 0, 1)),
            'scores': scores,
        }
