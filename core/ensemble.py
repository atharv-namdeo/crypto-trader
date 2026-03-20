"""
core/ensemble.py
Weighted Ensemble Scorer — Phase 1

Combines all 20 strategy signals (each returning direction + confidence)
into a single final_score ∈ [-1.0, +1.0].

final_score > +0.25  → LONG  (size scales with conviction)
final_score < -0.25  → SHORT
else                 → NEUTRAL (no trade or hold)
"""

import numpy as np


# ── Base weights (sum to 1.0 after normalization) ─────────────────────────
BASE_WEIGHTS = {
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

# Thresholds
SCORE_THRESHOLD_TRADE  = 0.25   # |score| > 0.25 → open trade
SCORE_THRESHOLD_STRONG = 0.55   # |score| > 0.55 → full-size trade
AGREEMENT_BONUS        = 0.20   # bonus when ≥70% of signals agree
AGREEMENT_RATIO_MIN    = 0.70


def _normalize_weights(weights: dict, signal_names: list) -> dict:
    """Keep only keys present in signal_names, renormalize to sum=1."""
    w = {k: weights.get(k, 0.0) for k in signal_names}
    total = sum(w.values())
    if total == 0:
        n = len(signal_names)
        return {k: 1.0 / n for k in signal_names}
    return {k: v / total for k, v in w.items()}


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
    confidence = np.clip(confidence, 0.0, 1.0)

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
    Combine all strategy signals into one ensemble result.

    Args:
        signal_map: dict mapping strategy name → signal dict
        regime: current market regime label
        regime_confidence: classifier confidence in the regime (0–1)

    Returns:
        {
          'final_score': float,   # ∈ [-1, +1]
          'action': str,          # 'LONG' | 'SHORT' | 'NEUTRAL'
          'conviction': float,    # 0–1, position size multiplier
          'signal_scores': dict,  # individual scores for logging
          'agreement_ratio': float,
        }
    """
    if not signal_map:
        return {'final_score': 0.0, 'action': 'NEUTRAL', 'conviction': 0.0,
                'signal_scores': {}, 'agreement_ratio': 0.0}

    # Convert each strategy signal → numeric score
    signal_scores = {name: signal_to_score(sig)
                     for name, sig in signal_map.items()}

    # Build regime-adjusted weights
    weights = dict(BASE_WEIGHTS)
    if regime in REGIME_WEIGHTS:
        weights.update(REGIME_WEIGHTS[regime])

    # Normalize to present signals only
    norm_weights = _normalize_weights(weights, list(signal_scores.keys()))

    # Weighted sum
    raw_score = sum(signal_scores[k] * norm_weights[k]
                    for k in signal_scores)

    # Agreement bonus: ≥70% signals pointing same direction
    bullish = sum(1 for v in signal_scores.values() if v > 0.1)
    bearish = sum(1 for v in signal_scores.values() if v < -0.1)
    total   = len(signal_scores)
    agreement_ratio = max(bullish, bearish) / (total + 1e-9)

    if agreement_ratio >= AGREEMENT_RATIO_MIN:
        # Apply bonus in direction of majority
        direction_sign = 1 if bullish > bearish else -1
        raw_score += direction_sign * AGREEMENT_BONUS

    # Scale by regime confidence (low confidence → dampen signal)
    confidence_scale = 0.5 + 0.5 * regime_confidence
    final_score = float(np.clip(raw_score * confidence_scale, -1.0, 1.0))

    # Determine action and conviction (0→1 position size multiplier)
    if final_score > SCORE_THRESHOLD_TRADE:
        action = 'LONG'
        conviction = min((final_score - SCORE_THRESHOLD_TRADE) /
                         (SCORE_THRESHOLD_STRONG - SCORE_THRESHOLD_TRADE), 1.0)
    elif final_score < -SCORE_THRESHOLD_TRADE:
        action = 'SHORT'
        conviction = min((abs(final_score) - SCORE_THRESHOLD_TRADE) /
                         (SCORE_THRESHOLD_STRONG - SCORE_THRESHOLD_TRADE), 1.0)
    else:
        action = 'NEUTRAL'
        conviction = 0.0

    return {
        'final_score':    final_score,
        'action':         action,
        'conviction':     float(conviction),
        'signal_scores':  signal_scores,
        'agreement_ratio': float(agreement_ratio),
        'regime':         regime,
    }
