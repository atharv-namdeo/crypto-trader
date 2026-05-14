import asyncio
import joblib
import time
import logging
import os
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor
from core.state_manager import StateManager

log = logging.getLogger("ParallelPredictor")

class ParallelMLPredictor:
    """
    Run multiple ML models in parallel and combine predictions.
    Uses ensemble voting for final signal.
    """
    
    def __init__(self, state: StateManager):
        self.state = state
        self.executor = ThreadPoolExecutor(max_workers=4)  # CPU-bound
        self._cache = {} # Inference cache: {symbol: {'ts': timestamp, 'pred': result}}
        
        self.model_paths = {
            'rf': 'ml/models/rf_altcoin.pkl',
            'gb': 'ml/models/gb_altcoin.pkl',
            'xgb': 'ml/models/xgb_altcoin.pkl',
            'lgb': 'ml/models/lgb_altcoin.pkl',
            'lstm': 'ml/models/lstm_altcoin.pkl',
        }
        
        self.models = {}
        self._load_all_models()
        
    def _load_all_models(self):
        for name, path in self.model_paths.items():
            try:
                if os.path.exists(path):
                    self.models[name] = joblib.load(path)
                    log.info(f"✅ Loaded model: {name}")
                else:
                    self.models[name] = None
                    log.warning(f"⚠️ Model not found: {path}")
            except Exception as e:
                log.error(f"❌ Error loading model {name}: {e}")
                self.models[name] = None

    async def predict_all(self, features: dict, symbol: str, timestamp: float = None) -> dict:
        """Run ALL models in PARALLEL and return ensemble prediction, with caching."""
        
        # Check cache if timestamp is provided (usually candle close time)
        if timestamp and symbol in self._cache:
            if self._cache[symbol]['ts'] == timestamp:
                log.debug(f"🎯 Cache HIT for {symbol} at {timestamp}")
                return self._cache[symbol]['pred']

        tasks = []
        
        # CPU-bound models via ThreadPool
        if self.models.get('rf'):
            tasks.append(self._run_model('rf', 'RF', features))
        if self.models.get('gb'):
            tasks.append(self._run_model('gb', 'GB', features))
        if self.models.get('xgb'):
            tasks.append(self._run_model('xgb', 'XGBoost', features))
        if self.models.get('lgb'):
            tasks.append(self._run_model('lgb', 'LightGBM', features))
        if self.models.get('lstm'):
            tasks.append(self._run_model('lstm', 'LSTM', features))
            
        if not tasks:
            return {'signal': 'HOLD', 'confidence': 0, 'ensemble_val': 0.5, 'reason': 'No models loaded'}
            
        start_time = time.time()
        results = await asyncio.gather(*tasks, return_exceptions=True)
        elapsed = time.time() - start_time
        
        log.info(f"⚡ Parallel prediction for {symbol} took {elapsed:.3f}s")
        
        # Phase 6: Fetch Dynamic Weights from Redis
        dynamic_weights = await self.state.get("ml:weights") or {
            'LightGBM': 10, 'RF': 8, 'GB': 7, 'XGBoost': 6, 'LSTM': 3
        }
        
        prediction = self._ensemble_vote(results, dynamic_weights)
        
        # Save to cache
        if timestamp:
            self._cache[symbol] = {'ts': timestamp, 'pred': prediction}
            
        return prediction

    async def _run_model(self, model_key: str, name: str, features: dict):
        """Run a specific model in a thread pool."""
        loop = asyncio.get_event_loop()
        try:
            # Most ML models expect 2D array [[]]
            feat_list = [list(features.values())]
            pred = await loop.run_in_executor(
                self.executor,
                lambda: self.models[model_key].predict(feat_list)
            )
            return {'model': name, 'prediction': float(pred[0])}
        except Exception as e:
            log.error(f"Error running {name}: {e}")
            raise e

    def _ensemble_vote(self, predictions: list, weights: dict) -> dict:
        """Weighted voting and direction consensus with dynamic ML weights."""
        valid_preds = [p for p in predictions if isinstance(p, dict)]
        if not valid_preds:
            return {'signal': 'HOLD', 'confidence': 0}
            
        total_weight = 0
        weighted_sum = 0
        
        for p in valid_preds:
            w = weights.get(p['model'], weights.get(p['model'].upper(), 5))
            weighted_sum += p['prediction'] * w
            total_weight += w
            
        ensemble_val = weighted_sum / total_weight
        
        # Tally votes for signal direction
        buy_votes = sum(1 for p in valid_preds if p['prediction'] > 0.55)
        sell_votes = sum(1 for p in valid_preds if p['prediction'] < 0.45)
        
        total = len(valid_preds)
        confidence = max(buy_votes, sell_votes) / total if total > 0 else 0
        
        if buy_votes > sell_votes and confidence > 0.5:
            signal = 'BUY'
        elif sell_votes > buy_votes and confidence > 0.5:
            signal = 'SELL'
        else:
            signal = 'HOLD'
            
        return {
            'signal': signal,
            'confidence': confidence,
            'ensemble_val': ensemble_val,
            'models_used': [p['model'] for p in valid_preds],
            'timestamp': time.time()
        }

    async def update_model_weights(self, accuracy_map: dict):
        """
        Public hook to update ensemble weights based on external accuracy tracking.
        accuracy_map: {'LightGBM': 0.65, 'RF': 0.58, ...}
        """
        # Convert accuracy (0.0 - 1.0) to weight (1 - 20)
        new_weights = {}
        for name, acc in accuracy_map.items():
            # Linear scaling: 50% acc -> 10 weight, 70% acc -> 20 weight
            weight = max(1, int((acc - 0.4) * 50)) 
            new_weights[name] = weight
            
        await self.state.set("ml:weights", new_weights)
        log.info(f"📈 Updated ML Ensemble Weights: {new_weights}")
