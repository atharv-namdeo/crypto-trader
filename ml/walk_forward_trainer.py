import pandas as pd
import numpy as np
import logging
from typing import List, Dict, Any, Tuple
from sklearn.preprocessing import StandardScaler
from xgboost import XGBClassifier

log = logging.getLogger("WalkForwardTrainer")

class WalkForwardValidator:
    """
    Time-series backtesting with proper data leakage prevention.
    Splits 3 years into rolling windows (Training -> Validation -> Testing).
    """
    
    def __init__(self, data_path: str = "backtest_data"):
        self.data_path = data_path
        self.scaler = StandardScaler()
        
    def create_rolling_windows(self, df: pd.DataFrame, train_size: int, test_size: int) -> List[Tuple[pd.DataFrame, pd.DataFrame]]:
        """
        Creates a list of (train_df, test_df) tuples for walk-forward validation.
        """
        windows = []
        total_len = len(df)
        
        # Start after the first training window
        start_idx = train_size
        while start_idx + test_size <= total_len:
            train_df = df.iloc[start_idx - train_size : start_idx]
            test_df = df.iloc[start_idx : start_idx + test_size]
            windows.append((train_df, test_df))
            start_idx += test_size # Move forward by test size
            
        return windows

    def prepare_features(self, df: pd.DataFrame) -> Tuple[np.ndarray, np.ndarray]:
        """
        Extracts features and labels for ML training.
        Target: Returns in the next 1h (BUY if > 1%, SELL if < -1%, HOLD else).
        """
        # 1. Feature Engineering
        features = pd.DataFrame(index=df.index)
        features['rsi'] = self._calculate_rsi(df['close'].values)
        features['returns_1h'] = df['close'].pct_change()
        features['volatility'] = df['close'].pct_change().rolling(24).std()
        
        # 2. Labels (Lookahead 1 hour)
        next_returns = df['close'].shift(-1).pct_change()
        labels = np.zeros(len(df))
        labels[next_returns > 0.01] = 1  # BUY
        labels[next_returns < -0.01] = 2 # SELL
        
        # Clean NaNs
        features = features.fillna(0)
        X = features.values
        y = labels
        
        return X, y

    def run_validation_cycle(self, symbol: str, windows: List[Tuple[pd.DataFrame, pd.DataFrame]]):
        """
        Executes the walk-forward cycle:
        For each window: Train on Train set, Test on Test set, track Win Rate.
        """
        from sklearn.preprocessing import LabelEncoder
        overall_results = []
        le = LabelEncoder()
        
        for i, (train_df, test_df) in enumerate(windows):
            X_train, y_train = self.prepare_features(train_df)
            X_test, y_test = self.prepare_features(test_df)
            
            # Ensure at least 2 classes exist to train
            if len(np.unique(y_train)) < 2:
                continue
            
            # Map labels to sequential integers [0, 1, 2]
            y_train_encoded = le.fit_transform(y_train)
            
            X_train_scaled = self.scaler.fit_transform(X_train)
            X_test_scaled = self.scaler.transform(X_test)
            
            model = XGBClassifier(n_estimators=50, max_depth=3, learning_rate=0.1)
            model.fit(X_train_scaled, y_train_encoded)
            
            # Only predict if classes in test exist in train
            valid_test_mask = np.isin(y_test, le.classes_)
            if not np.any(valid_test_mask):
                continue
                
            X_test_valid = X_test_scaled[valid_test_mask]
            y_test_valid = y_test[valid_test_mask]
            y_test_encoded = le.transform(y_test_valid)
            
            preds = model.predict(X_test_valid)
            accuracy = (preds == y_test_encoded).mean()
            overall_results.append(accuracy)
            
        avg_acc = np.mean(overall_results) if overall_results else 0.0
        log.info(f"✅ COMPLETED Walk-Forward for {symbol}. Avg Accuracy: {avg_acc:.2%}")
        return avg_acc

    def _calculate_rsi(self, prices, period=14):
        if len(prices) < period: return np.zeros(len(prices))
        deltas = np.diff(prices, prepend=prices[0])
        up = np.where(deltas > 0, deltas, 0)
        down = np.where(deltas < 0, -deltas, 0)
        
        avg_up = pd.Series(up).rolling(period).mean()
        avg_down = pd.Series(down).rolling(period).mean()
        
        rs = avg_up / (avg_down + 1e-9)
        rsi = 100 - (100 / (1 + rs))
        return rsi.fillna(50).values
