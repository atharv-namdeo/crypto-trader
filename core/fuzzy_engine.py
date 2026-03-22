import numpy as np

class FuzzyEngine:
    """
    Converts crisp indicator values into fuzzy membership scores [0, 1]
    then combines them with weighted AND/OR logic.
    """

    def rsi_oversold(self, rsi: float) -> float:
        """Membership: how oversold is RSI? 1.0 = extremely oversold"""
        if rsi <= 20: return 1.0
        if rsi >= 50: return 0.0
        return (50 - rsi) / 30  # linear from 50→20

    def rsi_overbought(self, rsi: float) -> float:
        """Membership: how overbought is RSI? 1.0 = extremely overbought"""
        if rsi >= 80: return 1.0
        if rsi <= 50: return 0.0
        return (rsi - 50) / 30

    def vwap_below(self, price: float, vwap: float) -> float:
        """Membership: how far below VWAP? 1.0 = very far below"""
        if vwap == 0: return 0.0
        dev = (vwap - price) / vwap
        if dev <= 0: return 0.0
        if dev >= 0.02: return 1.0
        return dev / 0.02  # 0% to 2% deviation maps to 0→1

    def vwap_above(self, price: float, vwap: float) -> float:
        if vwap == 0: return 0.0
        dev = (price - vwap) / vwap
        if dev <= 0: return 0.0
        if dev >= 0.02: return 1.0
        return dev / 0.02

    def volume_spike(self, vol_ratio: float) -> float:
        """Membership: how strong is volume? 1.0 = very strong"""
        if vol_ratio <= 1.0: return 0.0
        if vol_ratio >= 3.0: return 1.0
        return (vol_ratio - 1.0) / 2.0

    def trend_strength(self, adx: float) -> float:
        """Membership: how strong is the trend? 1.0 = very strong"""
        if adx <= 20: return 0.0
        if adx >= 50: return 1.0
        return (adx - 20) / 30

    def rsi_divergence(self, price_change: float, rsi_change: float) -> float:
        """Bullish divergence: price fell but RSI rose"""
        if price_change >= 0 or rsi_change <= 0:
            return 0.0
        # Both conditions met — score based on magnitude
        score = min(abs(price_change) * 100, 1.0) * min(rsi_change / 10, 1.0)
        return float(np.clip(score, 0, 1))

    def momentum_alignment(self, rsi_1m: float, rsi_5m: float, rsi_15m: float) -> float:
        """All timeframes aligned oversold = strong buy signal"""
        oversold_1m  = self.rsi_oversold(rsi_1m)
        oversold_5m  = self.rsi_oversold(rsi_5m)
        oversold_15m = self.rsi_oversold(rsi_15m)
        # Fuzzy AND = minimum (weakest link)
        return min(oversold_1m, oversold_5m, oversold_15m)

    def compute_long_score(self, indicators: dict) -> float:
        """
        Combine all fuzzy memberships into final BUY score [0, 1]
        Uses weighted fuzzy OR (max with weights)
        """
        scores = {
            'rsi_oversold':   (self.rsi_oversold(indicators.get('rsi', 50)),   0.30),
            'vwap_below':     (self.vwap_below(indicators.get('price', 0),
                               indicators.get('vwap', 0)),                      0.25),
            'volume_spike':   (self.volume_spike(indicators.get('vol_ratio', 1)), 0.20),
            'trend_strength': (self.trend_strength(indicators.get('adx', 0)),   0.15),
            'divergence':     (self.rsi_divergence(
                               indicators.get('price_change', 0),
                               indicators.get('rsi_change', 0)),                0.10),
        }
        # Weighted sum (fuzzy centroid defuzzification)
        total_weight = sum(w for _, w in scores.values())
        if total_weight == 0: return 0.0
        weighted_sum = sum(v * w for v, w in scores.values())
        return weighted_sum / total_weight

    def compute_short_score(self, indicators: dict) -> float:
        scores = {
            'rsi_overbought': (self.rsi_overbought(indicators.get('rsi', 50)), 0.30),
            'vwap_above':     (self.vwap_above(indicators.get('price', 0),
                               indicators.get('vwap', 0)),                     0.25),
            'volume_spike':   (self.volume_spike(indicators.get('vol_ratio', 1)), 0.20),
            'trend_strength': (self.trend_strength(indicators.get('adx', 0)),  0.15),
            'divergence':     (self.rsi_divergence(
                               -indicators.get('price_change', 0),
                               -indicators.get('rsi_change', 0)),              0.10),
        }
        total_weight = sum(w for _, w in scores.values())
        if total_weight == 0: return 0.0
        weighted_sum = sum(v * w for v, w in scores.values())
        return weighted_sum / total_weight

    def should_trade(self, long_score: float, short_score: float, strategy: str) -> tuple:
        """
        Defuzzify: convert fuzzy scores to crisp BUY/SELL/HOLD decision
        Thresholds vary by strategy aggressiveness
        """
        thresholds = {
            'SCALPER':  0.45,  # most aggressive, fires more often
            'SWING':    0.55,  # moderate
            'POSITION': 0.65,  # most conservative, only high conviction
        }
        threshold = thresholds.get(strategy, 0.50)

        if long_score > short_score and long_score >= threshold:
            return 'BUY', long_score
        elif short_score > long_score and short_score >= threshold:
            return 'SELL', short_score
        else:
            return 'HOLD', max(long_score, short_score)
