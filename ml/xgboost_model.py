"""
ml/xgboost_model.py
XGBoost Inference Engine — Phase 3
"""

import os
import joblib
import logging
from ml.feature_builder import build_feature_vector

log = logging.getLogger("XGBoostInference")

class XGBoostStrategy:
    def __init__(self):
        self.model_path = os.path.join(os.path.dirname(__file__), 'models', 'xgboost_btceth.pkl')
        self.model = None
        self.model_loaded = False

    async def load_model(self):
        import os, joblib
        path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "models", "xgboost_btceth.pkl")
        log.warning(f"XGBoost path: {path}")
        log.warning(f"File exists: {os.path.exists(path)}")
        log.warning(f"File size: {os.path.getsize(path) if os.path.exists(path) else 'N/A'}")
        try:
            self.model = joblib.load(path)
            self.model_loaded = True
            log.info("✅ XGBoost model loaded successfully")
        except Exception as e:
            log.error(f"❌ XGBoost load failed: {type(e).__name__}: {e}")

    def calculate_signal_from_features(self, feature_dict: dict) -> dict:
        """Called by main orchestrator every cycle."""
        if not getattr(self, 'model_loaded', False):
            return {'direction': 'NONE', 'confidence': 0.0}

        try:
            vec = build_feature_vector(feature_dict).reshape(1, -1)
            prob_up = float(self.model.predict_proba(vec)[0][1])  # Class 1 probability
            
            # Translate probability into LONG/SHORT confidence
            # If prob > 0.55 → LONG. If prob < 0.45 → SHORT.
            if prob_up > 0.55:
                # scale 0.55->1.0 to 0.1->1.0 confidence
                conf = min((prob_up - 0.55) / 0.45 + 0.1, 1.0)
                return {'direction': 'LONG', 'confidence': conf}
            elif prob_up < 0.45:
                # scale 0.45->0.0
                conf = min((0.45 - prob_up) / 0.45 + 0.1, 1.0)
                return {'direction': 'SHORT', 'confidence': conf}
            else:
                return {'direction': 'NONE', 'confidence': 0.0}
        except Exception as e:
            log.debug(f"XGBoost inference error: {e}")
            return {'direction': 'NONE', 'confidence': 0.0}
