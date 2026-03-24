"""
Boruta feature selection algorithm.
Based on: Omole & Enke (2024) - 'High-accuracy cryptocurrency forecasting with CNN-LSTM and Boruta feature selection'.
82.44% accuracy achieved using this method.
"""

import logging
import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestClassifier

log = logging.getLogger("BorutaSelector")

class BorutaSelector:
    def __init__(self, n_iterations: int = 20):
        self.n_iterations = n_iterations
        self.confirmed_features = []
        self.importance_scores = {}

    def select_features(self, df: pd.DataFrame, target: pd.Series, n_iterations: int = None) -> list:
        """
        Runs the 6-step Boruta algorithm to identify important features.
        """
        if n_iterations is None: n_iterations = self.n_iterations
        
        try:
            from sklearn.ensemble import RandomForestClassifier
        except ImportError:
            log.error("Boruta feature selection unavailable — install scikit-learn")
            return list(df.columns)

        log.info(f"🔍 Starting Boruta selection over {n_iterations} iterations...")
        
        # Ensure target is valid for classifier (convert to binary if needed)
        if target.dtype == 'float64':
            target = (target > target.shift(1)).astype(int)
            
        X = df.select_dtypes(include=[np.number]).copy()
        y = target.copy()
        
        # 1. & 2. Create Shadow Features
        feature_names = X.columns.tolist()
        hits = {feat: 0 for feat in feature_names}
        
        for i in range(n_iterations):
            # Duplicate and Shuffle shadow features
            X_shadow = X.apply(np.random.permutation)
            X_shadow.columns = ['shadow_' + feat for feat in feature_names]
            
            # Combine
            X_mixed = pd.concat([X, X_shadow], axis=1)
            
            # 3. Train Random Forest
            rf = RandomForestClassifier(n_estimators=100, random_state=42, n_jobs=-1)
            rf.fit(X_mixed, y)
            
            # 4. & 5. Compute Z-Scores and MZSA
            importances = rf.feature_importances_
            mzsa = importances[len(feature_names):].max()
            
            # 6. Label important features
            for idx, feat in enumerate(feature_names):
                if importances[idx] > mzsa:
                    hits[feat] += 1
            
            log.debug(f"Iteration {i+1}/{n_iterations} complete.")

        # Final decision: confirm features with hits > 50% iterations (simplified Boruta logic)
        self.confirmed_features = [feat for feat, hit_count in hits.items() if hit_count > (n_iterations / 2)]
        self.importance_scores = hits
        
        log.info(f"✅ Boruta selection complete. Confirmed {len(self.confirmed_features)} features as important.")
        return self.confirmed_features

    def get_importance_scores(self) -> dict:
        return self.importance_scores
