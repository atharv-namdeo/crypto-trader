import pandas as pd
import numpy as np
from typing import List, Tuple, Dict
import logging

log = logging.getLogger("PriceActionEngine")

class PriceActionZoneEngine:
    """
    Identifies high-probability support/resistance zones using:
    - Historical price reaction points (pivot clusters)
    - Volume profile (POC/VA)
    - Fibonacci retracements
    - Role reversals (Support <-> Resistance)
    """
    
    def __init__(self):
        self.FIBONACCI_RATIOS = [0.236, 0.382, 0.618, 0.786, 1.0]
        self.ZONE_WIDTH_PCT = 0.3  # 0.3% tolerance around fixed levels
    
    def find_major_zones(self, df: pd.DataFrame, window: int = 252) -> Dict[str, List[float]]:
        """
        Find major resistance and support zones over a lookback window.
        Uses clustering to find price levels that the market has respected multiple times.
        """
        if df is None or len(df) < 50:
            return {'resistance': [], 'support': []}
            
        df = df.tail(window).copy()
        highs = df['high'].values
        lows = df['low'].values
        
        # 1. Find local swing high/low points (Pivots)
        resistance_candidates = []
        support_candidates = []
        
        # Simple local extrema detection (window size 3)
        for i in range(2, len(df) - 2):
            # Potential resistance (Swing High)
            if highs[i] > highs[i-1] and highs[i] > highs[i-2] and \
               highs[i] > highs[i+1] and highs[i] > highs[i+2]:
                resistance_candidates.append(highs[i])
            
            # Potential support (Swing Low)
            if lows[i] < lows[i-1] and lows[i] < lows[i-2] and \
               lows[i] < lows[i+1] and lows[i] < lows[i+2]:
                support_candidates.append(lows[i])
        
        # 2. Add current 52-week High/Low as anchor points if not found
        resistance_candidates.append(df['high'].max())
        support_candidates.append(df['low'].min())
        
        # 3. Cluster candidates into actual zones
        resistance_zones = self._cluster_zones(resistance_candidates)
        support_zones = self._cluster_zones(support_candidates)
        
        return {
            'resistance': sorted(resistance_zones, reverse=True),
            'support': sorted(support_zones)
        }
    
    def calculate_fibonacci_levels(self, swing_low: float, swing_high: float) -> Dict[str, float]:
        """
        Calculate Fibonacci retracement levels for a given range.
        If swing_high > swing_low, calculates retracement for uptrend.
        """
        if swing_high == swing_low:
            return {}
            
        diff = swing_high - swing_low
        levels = {}
        
        for ratio in self.FIBONACCI_RATIOS:
            if swing_high > swing_low:  # Uptrend retrace
                level = swing_high - (diff * ratio)
            else:  # Downtrend retrace
                level = swing_low + (diff * ratio)
            
            levels[str(ratio)] = round(level, 8)
            
        return levels
    
    def _cluster_zones(self, levels: List[float], tolerance_pct: float = None) -> List[float]:
        """
        Merge individual reaction prices into consolidated zones using mean clustering.
        """
        if not levels: return []
        
        tol = tolerance_pct or self.ZONE_WIDTH_PCT
        sorted_levels = sorted(levels)
        clusters = []
        
        if not sorted_levels: return []
        
        current_cluster = [sorted_levels[0]]
        for level in sorted_levels[1:]:
            # If within tolerance of previous cluster member
            if abs(level - current_cluster[-1]) / current_cluster[-1] <= tol / 100:
                current_cluster.append(level)
            else:
                # Store the mean of the cluster as the representative level
                clusters.append(np.mean(current_cluster))
                current_cluster = [level]
        
        clusters.append(np.mean(current_cluster))
        return clusters

class ZoneTradeFilter:
    """
    Validation engine that ensures trade signals occur near structural 'confluence'.
    """
    def __init__(self, engine: PriceActionZoneEngine):
        self.engine = engine
        self.PROXIMITY_PCT = 0.005 # 0.5% proximity to level req for validation
        
    def validate_entry(self, side: str, price: float, zones: Dict, fibs: Dict) -> Tuple[bool, float]:
        """
        Gathers structural evidence to support or reject a trade entry.
        Returns (is_valid, confluence_score).
        """
        score = 0.0
        
        # 1. Proximity to S/R Zones
        relevant_zones = zones['support'] if side == 'BUY' else zones['resistance']
        for z in relevant_zones:
            if abs(price - z) / z <= self.PROXIMITY_PCT:
                score += 1.0
                break
                
        # 2. Proximity to Fib Levels
        for ratio, f_val in fibs.items():
            if abs(price - f_val) / f_val <= self.PROXIMITY_PCT:
                # Bonus for Golden Pocket (0.618)
                mult = 1.2 if ratio == "0.618" else 1.0
                score += (1.0 * mult)
                break
                
        # 3. Decision Logic: Need at least one major structural alignment
        is_valid = score >= 1.0
        
        return is_valid, score

def calculate_swing_points(df: pd.DataFrame, window: int = 30) -> Dict[str, float]:
    """Find major swing high and swing low in the recent window."""
    h_idx = df['high'].tail(window).idxmax()
    l_idx = df['low'].tail(window).idxmin()
    return {
        'high': float(df['high'].loc[h_idx]),
        'low': float(df['low'].loc[l_idx]),
        'high_time': h_idx,
        'low_time': l_idx
    }

def get_fib_retracements(low: float, high: float) -> Dict[str, float]:
    """Helper to get fib levels for a range."""
    engine = PriceActionZoneEngine()
    return engine.calculate_fibonacci_levels(low, high)
