"""
Weighted AI ensemble of FNN, LSTM, and GRU models.
Based on: Cohen & Aiche (2025) - 'A Hybrid Machine Learning Ensemble for Cryptocurrency Trading'.
Weights: FNN=0.4, LSTM=0.3, GRU=0.3. Signal: Buy (>0.6), Sell (<0.4), Hold (Else).
"""

import os
import torch
import torch.nn as nn
import logging
import numpy as np
from ml.feature_builder import FEATURE_KEYS
from ml.lstm_model import LSTMStrategy, QuantLSTM
from ml.gru_model import GRUStrategy, QuantGRU

log = logging.getLogger("EnsembleInference")

class FeedforwardModel(nn.Module):
    """3-layer MLP as specified in Paper 5."""
    def __init__(self, input_size):
        super(FeedforwardModel, self).__init__()
        self.network = nn.Sequential(
            nn.Linear(input_size, 128),
            nn.ReLU(),
            nn.Linear(128, 64),
            nn.ReLU(),
            nn.Linear(64, 1),
            nn.Sigmoid()
        )

    def forward(self, x):
        # Flatten the input sequence [batch, seq, features] -> [batch, seq*features]
        x = x.view(x.size(0), -1)
        return self.network(x)


class EnsembleModel:
    def __init__(self):
        self.seq_len = 60
        self.input_size = len(FEATURE_KEYS)
        self.weights = {"fnn": 0.4, "lstm": 0.3, "gru": 0.3}
        
        # Initialize sub-models
        self.fnn_model = FeedforwardModel(self.input_size * self.seq_len)
        self.lstm_strategy = LSTMStrategy()
        self.gru_strategy = GRUStrategy()
        
        self.fnn_path = os.path.join(os.path.dirname(__file__), 'models', 'fnn_btceth.pth')
        self._load_fnn()

    def _load_fnn(self):
        try:
            if os.path.exists(self.fnn_path):
                self.fnn_model.load_state_dict(torch.load(self.fnn_path))
                self.fnn_model.eval()
                log.info("✅ Loaded PyTorch FNN model")
            else:
                log.warning("⚠️ FNN model weights not found at %s. Initializing with random.", self.fnn_path)
                self.fnn_model.eval()
        except Exception as e:
            log.error(f"Failed to load FNN: {e}")

    def predict(self, feature_dict: dict) -> dict:
        """
        Calculates weighted average probability from FNN, LSTM, and GRU.
        Signal thresholds: BUY (>0.6), SELL (<0.4), HOLD (Else).
        """
        # Get individual component predictions
        # Note: LSTM and GRU maintain their own histories
        lstm_res = self.lstm_strategy.calculate_signal_from_features(feature_dict)
        gru_res = self.gru_strategy.calculate_signal_from_features(feature_dict)
        
        # Accessing private hist to feed FNN
        history = self.gru_strategy.history
        if len(history) < self.seq_len:
            return {
                "ensemble_prob": 0.5,
                "signal": "HOLD",
                "confidence": 0.0,
                "component_probs": {"fnn": 0.5, "lstm": 0.5, "gru": 0.5}
            }

        # FNN Prediction
        try:
            with torch.no_grad():
                seq_tensor = torch.tensor(np.array(history), dtype=torch.float32).unsqueeze(0)
                fnn_prob = float(self.fnn_model(seq_tensor).item())
        except Exception as e:
            log.error(f"FNN inference error: {e}")
            fnn_prob = 0.5

        # Get raw probs from components (falling back to 0.5 if NONE)
        lstm_prob = lstm_res.get('raw_prob', 0.5) if lstm_res['direction'] != 'NONE' else 0.5
        gru_prob = gru_res.get('raw_prob', 0.5) if gru_res['direction'] != 'HOLD' else 0.5

        # Weighted Ensemble Calculation
        ensemble_prob = (
            fnn_prob * self.weights['fnn'] +
            lstm_prob * self.weights['lstm'] +
            gru_prob * self.weights['gru']
        )

        signal = "HOLD"
        confidence = 0.0
        if ensemble_prob > 0.6:
            signal = "BUY"
            confidence = (ensemble_prob - 0.6) / 0.4
        elif ensemble_prob < 0.4:
            signal = "SELL"
            confidence = (0.4 - ensemble_prob) / 0.4

        return {
            "ensemble_prob": float(ensemble_prob),
            "signal": signal,
            "confidence": float(confidence),
            "component_probs": {
                "fnn": float(fnn_prob),
                "lstm": float(lstm_prob),
                "gru": float(gru_prob)
            }
        }
