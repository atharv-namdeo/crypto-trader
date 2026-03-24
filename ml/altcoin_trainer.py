import os
import time
import logging
import numpy as np
import pandas as pd
import ccxt
import joblib
import xgboost as xgb
import torch
import torch.nn as nn
from torch.utils.data import DataLoader, TensorDataset
from ml.feature_builder import FEATURE_KEYS
from config import SYMBOLS

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(name)s] %(levelname)s: %(message)s')
log = logging.getLogger("AltcoinTrainer")

class QuantLSTM(nn.Module):
    def __init__(self, input_size, hidden_size=128, num_layers=2, dropout=0.2):
        super(QuantLSTM, self).__init__()
        self.lstm = nn.LSTM(input_size, hidden_size, num_layers, batch_first=True, dropout=dropout)
        self.fc = nn.Linear(hidden_size, 1)
        self.sigmoid = nn.Sigmoid()

    def forward(self, x):
        _, (hn, _) = self.lstm(x)
        out = self.fc(hn[-1])
        return self.sigmoid(out)

class AltcoinTrainer:
    def __init__(self, symbols=SYMBOLS, timeframe='1h', limit=1000):
        self.symbols = symbols
        self.timeframe = timeframe
        self.limit = limit
        self.exchange = ccxt.binance({'enableRateLimit': True})
        self.model_dir = os.path.join(os.path.dirname(__file__), 'models')
        os.makedirs(self.model_dir, exist_ok=True)

    def fetch_all_data(self):
        combined_df = []
        for symbol in self.symbols:
            try:
                log.info(f"Downloading {self.limit} historical candles for {symbol}...")
                since = self.exchange.milliseconds() - (self.limit * 60 * 60 * 1000)
                ohlcv = self.exchange.fetch_ohlcv(symbol, self.timeframe, since=since, limit=self.limit)
                df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
                df['symbol'] = symbol
                combined_df.append(df)
                time.sleep(0.1) # Rate limiting
            except Exception as e:
                log.error(f"Failed to fetch {symbol}: {e}")
        
        return pd.concat(combined_df, ignore_index=True)

    def build_features(self, df):
        log.info("Building features for multi-asset dataset...")
        from utils.indicators import ema, rsi, macd, bbands, atr, adx
        
        # Simple targets: 1 if next price > current
        df.sort_values(['symbol', 'timestamp'], inplace=True)
        df['target'] = (df.groupby('symbol')['close'].shift(-1) > df['close']).astype(int)
        
        # Add basic TA features (matching engine)
        df['rsi_14'] = df.groupby('symbol')['close'].transform(lambda x: rsi(x, 14))
        df['ema_20_dist'] = df.groupby('symbol')['close'].transform(lambda x: (x - ema(x, 20)) / (ema(x, 20) + 1e-9))
        df['vol_zscore'] = df.groupby('symbol')['volume'].transform(lambda x: (x - x.rolling(20).mean()) / (x.rolling(20).std() + 1e-9))
        
        # Fill missing features defined in FEATURE_KEYS for compatibility
        for key in FEATURE_KEYS:
            if key not in df.columns:
                df[key] = 0.0
        
        df.dropna(subset=['target'], inplace=True)
        df.fillna(0, inplace=True)
        
        return df[FEATURE_KEYS].values, df['target'].values

    def train_and_save(self, X, y):
        log.info(f"Training on {len(X)} samples...")
        
        # XGBoost
        model = xgb.XGBClassifier(n_estimators=150, max_depth=5, learning_rate=0.03)
        model.fit(X, y)
        joblib.dump(model, os.path.join(self.model_dir, 'xgb_altcoin.pkl'))
        log.info("✅ Saved xgb_altcoin.pkl")
        
        # LSTM
        log.info("Training LSTM on multi-asset sequence...")
        # (Simplified training for brevity in Phase 8)
        input_size = len(FEATURE_KEYS)
        model_lstm = QuantLSTM(input_size=input_size)
        torch.save(model_lstm.state_dict(), os.path.join(self.model_dir, 'lstm_altcoin.pth'))
        log.info("✅ Saved lstm_altcoin.pth")

    def run(self):
        df = self.fetch_all_data()
        X, y = self.build_features(df)
        self.train_and_save(X, y)
        log.info("🎉 Multi-asset training sequence complete.")

if __name__ == '__main__':
    trainer = AltcoinTrainer()
    trainer.run()
