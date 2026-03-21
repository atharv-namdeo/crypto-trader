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
        self._load()

    def _load(self):
        import os
        path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "models", "xgboost_btceth.pkl")
        log.warning(f"XGBoost looking at: {path}")
        log.warning(f"ml/ contents: {os.listdir(os.path.dirname(os.path.abspath(__file__)))}")

        try:
            if os.path.exists(self.model_path):
                self.model = joblib.load(self.model_path)
                log.info("✅ Loaded XGBoost model")
            else:
                log.warning("⚠️ XGBoost model not found. Run trainer.py first.")
        except Exception as e:
            log.error(f"Failed to load XGBoost: {e}")

    def calculate_signal_from_features(self, feature_dict: dict) -> dict:
        """Called by main orchestrator every cycle."""
        if self.model is None:
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
