"""
Random Forest and Gradient Boosting price predictors.
Based on: Alnami et al. (2025) - 'Cryptocurrency Price Prediction using Machine Learning and Anomaly Detection'.
RF R²=0.9998 achieved on BTC.
"""

import os
import joblib
import logging
import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestRegressor, GradientBoostingRegressor
from sklearn.preprocessing import StandardScaler
from ml.anomaly_detector import AnomalyDetector

log = logging.getLogger("RFGBPredictor")

class RFGBPredictor:
    def __init__(self):
        self.rf_model = None
        self.gb_model = None
        self.scaler = StandardScaler()
        self.rf_path = os.path.join(os.path.dirname(__file__), 'models', 'rf_btceth.pkl')
        self.gb_path = os.path.join(os.path.dirname(__file__), 'models', 'gb_btceth.pkl')
        self.anomaly_detector = AnomalyDetector()
        self._load_models()

    def _load_models(self):
        try:
            if os.path.exists(self.rf_path):
                self.rf_model = joblib.load(self.rf_path)
                log.info("✅ Loaded Random Forest model")
            if os.path.exists(self.gb_path):
                self.gb_model = joblib.load(self.gb_path)
                log.info("✅ Loaded Gradient Boosting model")
        except Exception as e:
            log.error(f"Failed to load models: {e}")

    def predict_close(self, features_dict: dict) -> dict:
        """
        Predicts close price using RF and GB. Returns ensemble (mean) and direction.
        """
        if self.rf_model is None or self.gb_model is None:
            return {"rf_prediction": 0, "gb_prediction": 0, "direction": "HOLD", "confidence": 0}

        # Convert feature dict to 2D array for scaler/predictor
        # Note: Input features are Open, High, Low, Close, Volume, MarketCap (approx)
        # We'll use the FEATURE_KEYS subset or provided components
        try:
            input_data = np.array([[
                features_dict.get('open', 0),
                features_dict.get('high', 0),
                features_dict.get('low', 0),
                features_dict.get('close', 0),
                features_dict.get('volume', 0),
                features_dict.get('close', 0) * 1.0  # Proxy for MarketCap
            ]])
            
            # Note: Scaler needs to be fitted. If not fitted, we skip or use raw.
            # In a real scenario, we'd fit on a small history or load a saved scaler.
            rf_pred = float(self.rf_model.predict(input_data)[0])
            gb_pred = float(self.gb_model.predict(input_data)[0])
            ensemble_pred = (rf_pred + gb_pred) / 2.0
            
            current_close = features_dict.get('close', 0)
            direction = "UP" if ensemble_pred > current_close else "DOWN"
            confidence = abs(ensemble_pred - current_close) / (current_close + 1e-9)
            
            # Flag anomaly
            # anomaly = self.anomaly_detector.detect([current_close, ensemble_pred]) 
            # (Simplified anomaly check for prediction)
            
            return {
                "rf_prediction": rf_pred,
                "gb_prediction": gb_pred,
                "ensemble_prediction": ensemble_pred,
                "direction": direction,
                "confidence": float(np.clip(confidence * 10, 0, 1)) # Scaled confidence
            }
        except Exception as e:
            log.error(f"RF/GB Prediction error: {e}")
            return {"rf_prediction": 0, "gb_prediction": 0, "direction": "HOLD", "confidence": 0}

    def train(self, ohlcv_df: pd.DataFrame):
        """Train both regressors on provided data."""
        log.info("🚀 Training RF and GB predictors...")
        
        # Prepare features: O, H, L, C, V, Proxy-MC
        X = ohlcv_df[['open', 'high', 'low', 'close', 'volume']].copy()
        X['market_cap'] = X['close'] * 1.0 # Proxy
        y = ohlcv_df['close'].shift(-1).fillna(method='ffill') # Predict next close
        
        # Split
        split = int(len(X) * 0.8)
        X_train, X_test = X[:split], X[split:]
        y_train, y_test = y[:split], y[split:]
        
        # Train
        self.rf_model = RandomForestRegressor(n_estimators=100, random_state=42)
        self.gb_model = GradientBoostingRegressor(n_estimators=100, random_state=42)
        
        self.rf_model.fit(X_train, y_train)
        self.gb_model.fit(X_train, y_train)
        
        # Save
        os.makedirs(os.path.dirname(self.rf_path), exist_ok=True)
        joblib.dump(self.rf_model, self.rf_path)
        joblib.dump(self.gb_model, self.gb_path)
        
        log.info("✅ RF and GB predictors trained and saved.")
