import logging

log = logging.getLogger("TrainingScheduler")

class TrainingScheduler:
    """
    Manages the retraining intervals for all ML models based on market volatility and drift.
    """
    
    # Retirement/Retraining intervals in seconds
    SCHEDULE = {
        'LightGBM':      24 * 3600,   # Every 24 hours (fast models can be retrained daily)
        'RandomForest':  48 * 3600,   # Every 48 hours
        'XGBoost':       72 * 3600,   # Every 3 days
        'CatBoost':      7 * 24 * 3600,   # Weekly (best for structural patterns)
        'MLP':           7 * 24 * 3600,   # Weekly
        'LSTM':          30 * 24 * 3600,  # Monthly (deep models need stable data)
        'TRA':           30 * 24 * 3600,  # Monthly
        'Boruta':        7 * 24 * 3600    # Weekly feature selection
    }

    def needs_retraining(self, model_name: str, last_trained_ts: float, current_ts: float) -> bool:
        """Determines if a model should be retrained."""
        interval = self.SCHEDULE.get(model_name, 7 * 24 * 3600)
        if current_ts - last_trained_ts > interval:
            log.info(f"🔄 Retraining triggered for {model_name} (Interval: {interval/3600:.1f}h)")
            return True
        return False
