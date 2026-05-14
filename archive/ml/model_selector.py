import logging

log = logging.getLogger("ModelSelector")

class ModelSelector:
    """
    Selects the optimal ML model ensemble based on the strategy timeframe and available system resources.
    """
    
    # TIER 1: Ultra-Fast (Scalper - 1m timeframe)
    SCALPER_MODELS = {
        'models': ['LightGBM', 'RandomForest'],
        'max_latency_ms': 100,
        'update_interval': 30,
        'parallel': True
    }
    
    # TIER 2: Fast (Swing - 5m timeframe)
    SWING_MODELS = {
        'models': ['XGBoost', 'GradientBoosting', 'MLP'],
        'max_latency_ms': 500,
        'update_interval': 300,
        'parallel': True
    }
    
    # TIER 3: Accurate (Position - 15m timeframe)
    POSITION_MODELS = {
        'models': ['CatBoost', 'XGBoost', 'Boruta'],
        'max_latency_ms': 1000,
        'update_interval': 900,
        'parallel': True
    }
    
    # TIER 4: Advanced (Long-term - 1h+ timeframe)
    LONGTERM_MODELS = {
        'models': ['TRA', 'LSTM', 'CatBoost'],
        'max_latency_ms': 2000,
        'update_interval': 3600,
        'parallel': True
    }

    def get_models_for_strategy(self, strategy_type: str) -> dict:
        """Returns the model configuration for a given strategy."""
        strategy_map = {
            'SCALPER': self.SCALPER_MODELS,
            'SWING': self.SWING_MODELS,
            'POSITION': self.POSITION_MODELS,
            'ENSEMBLE': self.LONGTERM_MODELS,
            'MEAN_REVERSION': self.SWING_MODELS, # Use swing models for 5m MR
            'ENSEMBLE_VOTE': self.POSITION_MODELS  # Use position models for voting
        }
        
        config = strategy_map.get(strategy_type.upper(), self.SWING_MODELS)
        log.info(f"🎯 Selected {len(config['models'])} models for {strategy_type}")
        return config
