import joblib
import os
import xgboost as xgb
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("ModelMigrator")

def migrate_xgboost():
    model_path = 'ml/models/xgboost_btceth.pkl'
    if not os.path.exists(model_path):
        logger.error(f"Model not found at {model_path}")
        return

    try:
        logger.info(f"Loading model from {model_path}...")
        # Load the old model
        model = joblib.load(model_path)
        
        # Re-save it using the current XGBoost version
        # If it's a Booster object, we can save it as .json or .model for better compatibility
        # But for now, we'll just re-pickle it (or use save_model if possible)
        
        logger.info(f"Successfully loaded. Re-saving for compatibility...")
        
        # If the loaded object is an XGBoost model, try to use its save_model method
        if hasattr(model, 'save_model'):
            # Save as native xgboost format
            native_path = 'ml/models/xgboost_btceth.model'
            model.save_model(native_path)
            logger.info(f"Saved native XGBoost model to {native_path}")
        
        # Also re-pickle it to satisfy joblib.load in the existing code
        joblib.dump(model, model_path)
        logger.info(f"Re-pickled model to {model_path}")

    except Exception as e:
        logger.error(f"Migration failed: {e}")

if __name__ == "__main__":
    migrate_xgboost()
