"""
core/ensemble.py
Score-Based Ensemble — Phase 3

Combines all strategy scores into a forced BUY / SELL / NEUTRAL decision.
Strategies return float ∈ [-1, +1]. Ensemble uses weighted average + quorum.
"""

import logging

log = logging.getLogger("Ensemble")

# ── Base weights ─────────────────────────────────────────────────
BASE_WEIGHTS = {
    'XGBOOST':         0.15,
    'LSTM':            0.15,
    'MTF':             0.08,
    'MTF_MACD':        0.06,
    'MEAN_REVERSION':  0.06,
    'BREAKOUT':        0.06,
    'OBIS':            0.04,
    'VWAP_REVERSION':  0.04,
    'LIQUIDITY_SWEEP': 0.04,
    'RSI_DIV':         0.04,
    'FIBONACCI':       0.03,
    'ICHIMOKU':        0.04,
    'ATR_EXPANSION':   0.03,
    'VOLUME_PROFILE':  0.03,
    'PIVOT_POINTS':    0.03,
    'PSAR':            0.03,
    'SUPERTREND':      0.04,
    'GANN_FAN':        0.02,
    'HARMONIC':        0.02,
    'LIQUIDITY_GRAB':  0.03,
    'TREND_EXHAUST':   0.03,
    'STAT_ARB':        0.03,
}


def compute_ensemble(
    score_map: dict,        # {strategy_name: float score}
    regime: str = 'CHOPPY_NOISE',
    regime_confidence: float = 0.5,
) -> dict:
    """
    Weighted-average ensemble: forced BUY / SELL / NEUTRAL decision.

    Args:
        score_map: dict mapping strategy name → float score ∈ [-1, +1]
        regime: current market regime label
        regime_confidence: classifier confidence in the regime (0-1)

    Returns:
        {
          'action': str,          # 'BUY' | 'SELL' | 'NEUTRAL'
          'score': float,         # weighted average score
          'conviction': float,    # 0-1
          'long_votes': int,
          'short_votes': int,
          'regime': str,
          'signal_scores': dict,
        }
    """
    if not score_map:
        return {
            'action': 'NEUTRAL', 'score': 0.0, 'conviction': 0.0,
            'long_votes': 0, 'short_votes': 0, 'regime': regime,
            'signal_scores': {},
        }

    total_signals = len(score_map)

    # Count directional votes
    long_votes = sum(1 for v in score_map.values() if v > 0.05)
    short_votes = sum(1 for v in score_map.values() if v < -0.05)

    # Weighted average score
    total_weight = 0.0
    weighted_sum = 0.0
    for name, score in score_map.items():
        w = BASE_WEIGHTS.get(name, 0.03)
        weighted_sum += w * score
        total_weight += w

    raw_score = weighted_sum / (total_weight + 1e-9)

    # Debug logging
    for name, score in score_map.items():
        if abs(score) > 0.05:
            log.info(f"  [SIGNAL] {name}={score:+.3f}")
    log.info(f"  [RAW_SCORE] weighted={raw_score:+.4f} "
             f"long={long_votes} short={short_votes}")

    # ── FORCED DECISION ──
    if long_votes > short_votes and long_votes > total_signals * 0.25:
        action = "BUY"
        conviction = abs(raw_score)
    elif short_votes > long_votes and short_votes > total_signals * 0.25:
        action = "SELL"
        conviction = abs(raw_score)
    elif abs(raw_score) > 0.08:
        # Tiebreaker: use weighted score
        action = "BUY" if raw_score > 0 else "SELL"
        conviction = abs(raw_score)
    else:
        action = "NEUTRAL"
        conviction = 0.0

    return {
        'action':         action,
        'score':          float(raw_score),
        'conviction':     float(min(conviction, 1.0)),
        'long_votes':     long_votes,
        'short_votes':    short_votes,
        'regime':         regime,
        'signal_scores':  score_map,
    }
