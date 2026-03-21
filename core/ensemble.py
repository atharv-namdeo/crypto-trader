"""
core/ensemble.py
Majority-Vote Ensemble Scorer — Phase 2

Combines all strategy signals into a forced BUY / SELL / NEUTRAL decision
every cycle. No threshold gating — majority vote with 25% quorum.
"""

import logging

log = logging.getLogger("Ensemble")

# ── Base weights (sum to 1.0 after normalization) ─────────────────────────
BASE_WEIGHTS = {
    'XGBOOST':         0.25,
    'LSTM':            0.25,
    'MTF':             0.10,
    'MTF_MACD':        0.07,
    'MEAN_REVERSION':  0.08,
    'BREAKOUT':        0.07,
    'OBIS':            0.06,
    'VWAP_REVERSION':  0.05,
    'LIQUIDITY_SWEEP': 0.05,
    'RSI_DIV':         0.05,
    'FIBONACCI':       0.04,
    'ICHIMOKU':        0.05,
    'ATR_EXPANSION':   0.04,
    'VOLUME_PROFILE':  0.04,
    'PIVOT_POINTS':    0.04,
    'PSAR':            0.04,
    'SUPERTREND':      0.06,
    'GANN_FAN':        0.03,
    'HARMONIC':        0.03,
    'LIQUIDITY_GRAB':  0.04,
    'TREND_EXHAUST':   0.04,
    'STAT_ARB':        0.04,
}

# ── Regime-specific weight overrides (merged into BASE_WEIGHTS) ───────────
REGIME_WEIGHTS = {
    'TRENDING_BULL': {
        'MTF': 0.18, 'MTF_MACD': 0.12, 'SUPERTREND': 0.10,
        'BREAKOUT': 0.10, 'ICHIMOKU': 0.08, 'TREND_EXHAUST': 0.06,
        'MEAN_REVERSION': 0.02, 'VWAP_REVERSION': 0.02, 'RSI_DIV': 0.02,
    },
    'TRENDING_BEAR': {
        'MTF': 0.18, 'MTF_MACD': 0.12, 'SUPERTREND': 0.10,
        'BREAKOUT': 0.10, 'ICHIMOKU': 0.08, 'TREND_EXHAUST': 0.06,
        'MEAN_REVERSION': 0.02, 'VWAP_REVERSION': 0.02, 'RSI_DIV': 0.02,
    },
    'MEAN_REVERTING': {
        'MEAN_REVERSION': 0.16, 'VWAP_REVERSION': 0.12, 'RSI_DIV': 0.10,
        'STAT_ARB': 0.10, 'FIBONACCI': 0.08, 'PIVOT_POINTS': 0.07,
        'MTF': 0.03, 'BREAKOUT': 0.02, 'MTF_MACD': 0.03,
    },
    'HIGH_VOLATILITY': {
        'OBIS': 0.14, 'LIQUIDITY_SWEEP': 0.12, 'LIQUIDITY_GRAB': 0.10,
        'ATR_EXPANSION': 0.10, 'BREAKOUT': 0.08,
        'MEAN_REVERSION': 0.02, 'SUPERTREND': 0.03,
    },
    'BREAKOUT_PENDING': {
        'BREAKOUT': 0.18, 'HARMONIC': 0.10, 'VOLUME_PROFILE': 0.10,
        'LIQUIDITY_SWEEP': 0.09, 'PIVOT_POINTS': 0.08, 'ATR_EXPANSION': 0.08,
        'MEAN_REVERSION': 0.02, 'MTF': 0.04,
    },
    'CHOPPY_NOISE': {
        'STAT_ARB': 0.14, 'PIVOT_POINTS': 0.12, 'VWAP_REVERSION': 0.12,
        'LIQUIDITY_SWEEP': 0.10, 'OBIS': 0.08, 'FIBONACCI': 0.07,
        'MTF': 0.02, 'BREAKOUT': 0.01,
    },
}


def signal_to_score(signal: dict) -> float:
    """
    Convert a strategy's output dict to a score ∈ [-1, +1].

    Strategy signals typically look like:
        {'direction': 'LONG', 'confidence': 0.7, ...}   → +0.7
        {'direction': 'SHORT', 'confidence': 0.6, ...}  → -0.6
        {'direction': 'NONE', ...}                       →  0.0
    """
    direction = signal.get('direction', 'NONE')
    confidence = float(signal.get('confidence', signal.get('score', 0.5)))
    confidence = max(0.0, min(1.0, confidence))

    if direction == 'LONG':
        return confidence
    elif direction == 'SHORT':
        return -confidence
    else:
        return 0.0


def compute_ensemble(
    signal_map: dict,      # {strategy_name: signal_dict}
    regime: str = 'CHOPPY_NOISE',
    regime_confidence: float = 0.5,
) -> dict:
    """
    Majority-vote ensemble: forced BUY / SELL / NEUTRAL decision.

    Instead of threshold-gating, counts directional votes.
    25% quorum required for BUY or SELL; otherwise NEUTRAL.

    Args:
        signal_map: dict mapping strategy name → signal dict
        regime: current market regime label
        regime_confidence: classifier confidence in the regime (0–1)

    Returns:
        {
          'action': str,          # 'BUY' | 'SELL' | 'NEUTRAL'
          'score': float,         # average raw score
          'conviction': float,    # 0–1 ratio of votes in winning direction
          'long_votes': int,
          'short_votes': int,
          'regime': str,
          'signal_scores': dict,
        }
    """
    if not signal_map:
        return {
            'action': 'NEUTRAL', 'score': 0.0, 'conviction': 0.0,
            'long_votes': 0, 'short_votes': 0, 'regime': regime,
            'signal_scores': {},
        }

    # Convert each strategy signal → numeric score
    signal_scores = {name: signal_to_score(sig)
                     for name, sig in signal_map.items()}

    total_signals = len(signal_scores)

    # Count directional votes
    long_votes = sum(1 for v in signal_scores.values() if v > 0.1)
    short_votes = sum(1 for v in signal_scores.values() if v < -0.1)
    neutral = total_signals - long_votes - short_votes

    # Weighted average score
    raw_score = sum(signal_scores.values()) / total_signals

    # ── FORCED DECISION — always pick one ──
    if long_votes > short_votes and long_votes > total_signals * 0.25:
        action = "BUY"
        conviction = long_votes / total_signals
    elif short_votes > long_votes and short_votes > total_signals * 0.25:
        action = "SELL"
        conviction = short_votes / total_signals
    else:
        action = "NEUTRAL"
        conviction = 0.0

    # If votes are too low but raw score is strong, use it as tiebreaker
    if action == "NEUTRAL" and abs(raw_score) > 0.15:
        action = "BUY" if raw_score > 0 else "SELL"
        conviction = abs(raw_score)

    return {
        'action':         action,
        'score':          float(raw_score),
        'conviction':     float(conviction),
        'long_votes':     long_votes,
        'short_votes':    short_votes,
        'regime':         regime,
        'signal_scores':  signal_scores,
    }
