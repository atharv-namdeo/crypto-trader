"""
Z-Score rolling anomaly detection algorithm. 
Based on: Alnami et al. (2025) - 'Cryptocurrency Price Prediction using Machine Learning and Anomaly Detection'.
Uses rolling mean and standard deviation to flag abnormal price events.
"""

import logging
import numpy as np

log = logging.getLogger("AnomalyDetector")

class AnomalyDetector:
    def __init__(self, window: int = 30, threshold: float = 1.0):
        self.window = window
        self.threshold = threshold

    def detect(self, prices: list, window: int = None, threshold: float = None) -> dict:
        """
        Flag as abnormal if |Z(t)| > threshold.
        Returns: {"is_abnormal": bool, "z_score": float, "rolling_mean": float, "rolling_std": float, "abnormality_indicator": int}
        """
        if window is None: window = self.window
        if threshold is None: threshold = self.threshold

        if len(prices) < window:
            return {
                "is_abnormal": False,
                "z_score": 0.0,
                "rolling_mean": 0.0,
                "rolling_std": 0.0,
                "abnormality_indicator": 0
            }

        recent_prices = np.array(prices[-window:])
        current_price = float(prices[-1])
        
        mu = float(np.mean(recent_prices))
        sigma = float(np.std(recent_prices))
        
        if sigma == 0:
            z_score = 0.0
        else:
            z_score = (current_price - mu) / sigma
            
        is_abnormal = abs(z_score) > threshold
        
        if is_abnormal:
            log.warning(f"🚨 Anomaly Detected! Z-Score: {z_score:.2f} (Threshold: {threshold}) at price {current_price:.2f}")

        return {
            "is_abnormal": bool(is_abnormal),
            "z_score": float(z_score),
            "rolling_mean": float(mu),
            "rolling_std": float(sigma),
            "abnormality_indicator": 1 if is_abnormal else 0
        }

    def detect_batch(self, prices: list, window: int = None, threshold: float = None) -> list:
        """Process a series of prices and return a list of anomaly results."""
        if window is None: window = self.window
        results = []
        for i in range(len(prices)):
            if i < window:
                results.append(self.detect([], window, threshold))
            else:
                results.append(self.detect(prices[:i+1], window, threshold))
        return results

def detect_anomaly(prices: list, window: int = 30, threshold: float = 1.0) -> dict:
    """Helper function for quick detection."""
    detector = AnomalyDetector(window=window, threshold=threshold)
    return detector.detect(prices)
