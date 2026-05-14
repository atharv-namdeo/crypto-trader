"""
ml/lstm_model.py
LSTM Inference Engine — Phase 3
"""

import os
import torch
import torch.nn as nn
import logging
import numpy as np
from ml.feature_builder import build_feature_vector, FEATURE_KEYS

log = logging.getLogger("LSTMInference")

class QuantLSTM(nn.Module):
    """Must match trainer exactly."""
    def __init__(self, input_size, hidden_size=128, num_layers=2, dropout=0.2):
        super(QuantLSTM, self).__init__()
        self.lstm = nn.LSTM(input_size, hidden_size, num_layers, batch_first=True, dropout=dropout)
        self.fc = nn.Linear(hidden_size, 1)
        self.sigmoid = nn.Sigmoid()

    def forward(self, x):
        _, (hn, _) = self.lstm(x)
        out = self.fc(hn[-1])
        return self.sigmoid(out)


class LSTMStrategy:
    def __init__(self):
        self.model_path = os.path.join(os.path.dirname(__file__), 'models', 'lstm_btceth.pth')
        self.model = None
        self.history = []  # rolling window of 60 vectors
        self.seq_len = 60
        self._load()

    def _load(self):
        try:
            if os.path.exists(self.model_path):
                self.model = QuantLSTM(input_size=len(FEATURE_KEYS))
                self.model.load_state_dict(torch.load(self.model_path))
                self.model.eval()
                log.info("✅ Loaded PyTorch LSTM model")
            else:
                log.warning("⚠️ LSTM model not found. Run trainer.py first.")
        except Exception as e:
            log.error(f"Failed to load LSTM: {e}")

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
                return {'direction': 'LONG', 'confidence': conf}
            elif prob_up < 0.45:
                conf = min((0.45 - prob_up) / 0.45 + 0.1, 1.0)
                return {'direction': 'SHORT', 'confidence': conf}
            else:
                return {'direction': 'NONE', 'confidence': 0.0}
                
        except Exception as e:
            log.debug(f"LSTM inference error: {e}")
            return {'direction': 'NONE', 'confidence': 0.0}
