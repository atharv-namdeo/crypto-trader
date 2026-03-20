"""
ml/trainer.py
Automated ML Trainer Pipeline — Phase 3

Fetches historical data, computes features matching ml/feature_builder.py,
trains XGBoost and LSTM models, and saves them to ml/models/.
"""

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

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(name)s] %(levelname)s: %(message)s')
log = logging.getLogger("Trainer")

# --- LSTM Definition ---
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

class MLTrainer:
    def __init__(self, symbol='BTC/USDT', timeframe='1h', limit=4000):
        self.symbol = symbol
        self.timeframe = timeframe
        self.limit = limit
        self.exchange = ccxt.binance({'enableRateLimit': True})
        self.model_dir = os.path.join(os.path.dirname(__file__), 'models')
        os.makedirs(self.model_dir, exist_ok=True)

    def fetch_data(self):
        log.info(f"Downloading {self.limit} historical {self.timeframe} candles for {self.symbol}...")
        all_ohlcv = []
        since = self.exchange.milliseconds() - (self.limit * 60 * 60 * 1000)
        
        while len(all_ohlcv) < self.limit:
            page = self.exchange.fetch_ohlcv(self.symbol, self.timeframe, since=since, limit=1000)
            if not page:
                break
            all_ohlcv.extend(page)
            since = page[-1][0] + 1
            time.sleep(0.1)

        # Truncate to limit and convert to DF
        all_ohlcv = all_ohlcv[-self.limit:]
        df = pd.DataFrame(all_ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
        log.info(f"Downloaded {len(df)} candles.")
        return df

    def build_dataset(self, df):
        log.info("Computing TA features to match feature_builder.py...")
        from utils.indicators import ema, rsi, macd, bbands, atr, adx
        
        # We simulate the exact dictionary keys. Features requiring 1m data will be approximated or zeroed.
        for n in [1, 3, 5, 10, 20]:
            df[f'log_return_{n}m'] = 0.0  # Cannot compute 1m returns on 1h df easily for MVP
        
        df['log_return_60m'] = np.log(df['close'] / df['close'].shift(1)).fillna(0)
        
        c_range = np.maximum((df['high'] - df['low']), 1e-9)
        df['candle_body'] = abs(df['open'] - df['close']) / c_range
        df['upper_wick'] = (df['high'] - df[['open', 'close']].max(axis=1)) / c_range
        df['lower_wick'] = (df[['open', 'close']].min(axis=1) - df['low']) / c_range
        
        for p in [9, 21, 50, 200]:
            ema_s = ema(df['close'], p)
            df[f'ema_{p}_dist'] = (df['close'] - ema_s) / (ema_s + 1e-9)

        adx_res = adx(df['high'], df['low'], df['close'], 14)
        df['adx_14'] = adx_res['ADX_14']
        df['adx_pos_di'] = adx_res['DMP_14']
        df['adx_neg_di'] = adx_res['DMN_14']
        df['adx_slope_3'] = df['adx_14'] - df['adx_14'].shift(3)

        macd_res = macd(df['close'])
        df['macd_line'] = macd_res.iloc[:, 0]
        df['macd_signal'] = macd_res.iloc[:, 2]
        df['macd_histogram'] = macd_res.iloc[:, 1]
        df['macd_hist_slope'] = df['macd_histogram'] - df['macd_histogram'].shift(3)

        df['rsi_14_1h'] = rsi(df['close'], 14)
        df['rsi_7_1h'] = rsi(df['close'], 7)
        df['rsi_21_1h'] = rsi(df['close'], 21)
        df['rsi_14_1m'] = df['rsi_14_1h'] # approx
        
        df['stoch_k'] = df['rsi_14_1h'] / 100.0 # stoch unavailable in utils, rough proxy
        df['stoch_d'] = df['stoch_k'].rolling(3).mean()

        bb = bbands(df['close'], 20, 2.0)
        df['bb_width'] = (bb.iloc[:, 2] - bb.iloc[:, 0]) / (bb.iloc[:, 1] + 1e-9)
        df['bb_position'] = (df['close'] - bb.iloc[:, 0]) / (bb.iloc[:, 2] - bb.iloc[:, 0] + 1e-9)
        df['bb_width_pct_90d'] = 50.0  # placeholder
        
        df['realized_vol_14h'] = df['close'].pct_change().rolling(14).std() * np.sqrt(24*365)
        df['atr_14_1h'] = atr(df['high'], df['low'], df['close'], 14)
        df['atr_14_1m'] = df['atr_14_1h'] / 60.0 # approx

        df['volume_ratio'] = df['volume'] / (df['volume'].rolling(20).mean() + 1e-9)
        df['volume_zscore'] = (df['volume'] - df['volume'].rolling(20).mean()) / (df['volume'].rolling(20).std() + 1e-9)
        
        for col in ['cvd_1m', 'trade_imbalance', 'ob_imbalance', 'spread_normalized', 'microprice_vs_mid', 'vwap_zscore']:
            df[col] = 0.0
            
        # Target: 1 if next candle close > current close, else 0
        df['target'] = (df['close'].shift(-1) > df['close']).astype(int)
        
        df.replace([np.inf, -np.inf], np.nan, inplace=True)
        df.fillna(0, inplace=True)
        
        # Ensure correct order
        X = df[FEATURE_KEYS].values
        y = df['target'].values
        return X, y

    def train_xgboost(self, X, y):
        log.info("🌲 Training XGBoost Model...")
        # Split train/test (80/20 chronologically)
        split = int(len(X) * 0.8)
        X_train, X_test = X[:split], X[split:]
        y_train, y_test = y[:split], y[split:]
        
        model = xgb.XGBClassifier(
            n_estimators=100, max_depth=4, learning_rate=0.05,
            objective='binary:logistic', random_state=42
        )
        model.fit(X_train, y_train, eval_set=[(X_test, y_test)], verbose=False)
        
        acc = (model.predict(X_test) == y_test).mean()
        log.info(f"✅ XGBoost Accuracy on Test Set: {acc:.2%}")
        joblib.dump(model, os.path.join(self.model_dir, 'xgboost.pkl'))

    def train_lstm(self, X, y):
        log.info("🧠 Training LSTM Model (60-step lookback)...")
        seq_len = 60
        X_seq, y_seq = [], []
        for i in range(len(X) - seq_len):
            X_seq.append(X[i:i+seq_len])
            y_seq.append(y[i+seq_len])
            
        X_seq = torch.tensor(np.array(X_seq), dtype=torch.float32)
        y_seq = torch.tensor(np.array(y_seq), dtype=torch.float32).unsqueeze(1)
        
        split = int(len(X_seq) * 0.8)
        train_data = TensorDataset(X_seq[:split], y_seq[:split])
        train_loader = DataLoader(train_data, batch_size=64, shuffle=True)
        
        model = QuantLSTM(input_size=len(FEATURE_KEYS))
        criterion = nn.BCELoss()
        optimizer = torch.optim.Adam(model.parameters(), lr=0.001)
        
        epochs = 10
        for epoch in range(epochs):
            model.train()
            total_loss = 0
            for batch_X, batch_y in train_loader:
                optimizer.zero_grad()
                outputs = model(batch_X)
                loss = criterion(outputs, batch_y)
                loss.backward()
                optimizer.step()
                total_loss += loss.item()
                
        model.eval()
        with torch.no_grad():
            preds = model(X_seq[split:])
            acc = ((preds > 0.5).float() == y_seq[split:]).float().mean()
        log.info(f"✅ LSTM Test Accuracy: {acc:.2%} (Loss: {total_loss/len(train_loader):.4f})")
        torch.save(model.state_dict(), os.path.join(self.model_dir, 'lstm.pth'))

    def run(self):
        log.info("=== Starting Automated ML Pipeline ===")
        df = self.fetch_data()
        X, y = self.build_dataset(df)
        self.train_xgboost(X, y)
        self.train_lstm(X, y)
        log.info("🎉 All models trained and saved to ml/models/")

if __name__ == '__main__':
    trainer = MLTrainer()
    trainer.run()
