"""
GRU model for high-frequency cryptocurrency price forecasting. 
Based on: Rodrigues & Machado (2025) - 'High-Frequency Cryptocurrency Price Forecasting Using Machine Learning Models: A Comparative Study'. 
MAPE=0.09%, GRU outperforms LSTM for 60-min forecasting.
"""

import os
import torch
import torch.nn as nn
import logging
import numpy as np
from ml.feature_builder import build_feature_vector, FEATURE_KEYS

log = logging.getLogger("GRUInference")

class QuantGRU(nn.Module):
    """Must match trainer exactly."""
    def __init__(self, input_size, hidden_size=50, num_layers=2, dropout=0.2):
        super(QuantGRU, self).__init__()
        self.gru = nn.GRU(input_size, hidden_size, num_layers, batch_first=True, dropout=dropout)
        self.fc = nn.Linear(hidden_size, 1)
        self.sigmoid = nn.Sigmoid()

    def forward(self, x):
        _, hn = self.gru(x)
        out = self.fc(hn[-1])
        return self.sigmoid(out)


class GRUStrategy:
    def __init__(self):
        self.model_path = os.path.join(os.path.dirname(__file__), 'models', 'gru_btceth.pth')
        self.model = None
        self.history = []  # rolling window of 60 vectors
        self.seq_len = 60
        self._load()

    def _load(self):
        try:
            if os.path.exists(self.model_path):
                self.model = QuantGRU(input_size=len(FEATURE_KEYS))
                self.model.load_state_dict(torch.load(self.model_path))
                self.model.eval()
                log.info("✅ Loaded PyTorch GRU model")
            else:
                log.warning("⚠️ GRU model weights not found at %s. Initializing with random weights for now.", self.model_path)
                self.model = QuantGRU(input_size=len(FEATURE_KEYS))
                self.model.eval()
        except Exception as e:
            log.error(f"Failed to load GRU: {e}")

    def calculate_signal_from_features(self, feature_dict: dict) -> dict:
        """Called by main orchestrator every cycle."""
        if self.model is None:
            return {'direction': 'NONE', 'confidence': 0.0}

        try:
            vec = build_feature_vector(feature_dict)
            self.history.append(vec)
            
            # Maintain 60-step lookback window
            if len(self.history) > self.seq_len:
                self.history = self.history[-self.seq_len:]
                
            if len(self.history) < self.seq_len:
                return {'direction': 'NONE', 'confidence': 0.0}

            # Inference
            with torch.no_grad():
                seq_tensor = torch.tensor(np.array(self.history), dtype=torch.float32).unsqueeze(0)  # batch_size=1
                prob_up = float(self.model(seq_tensor).item())

            if prob_up > 0.55:
                conf = min((prob_up - 0.55) / 0.45 + 0.1, 1.0)
                return {'direction': 'BUY', 'confidence': conf, 'raw_prob': prob_up}
            elif prob_up < 0.45:
                conf = min((0.45 - prob_up) / 0.45 + 0.1, 1.0)
                return {'direction': 'SELL', 'confidence': conf, 'raw_prob': prob_up}
            else:
                return {'direction': 'HOLD', 'confidence': 0.0, 'raw_prob': prob_up}
                
        except Exception as e:
            log.error(f"GRU inference error: {e}")
            return {'direction': 'HOLD', 'confidence': 0.0, 'raw_prob': 0.5}

    def predict(self, feature_dict: dict) -> dict:
        """Explicitly requested method name from instructions."""
        return self.calculate_signal_from_features(feature_dict)

    def get_forecast_horizon_label(self, minutes: int) -> str:
        """Returns labels as per paper constraints."""
        if minutes <= 60: return "short"
        if minutes <= 240: return "medium"
        return "long"
