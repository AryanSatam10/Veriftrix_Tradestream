import os
import joblib
import pandas as pd
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler
from utils import setup_logger, engineer_features, get_feature_columns

logger = setup_logger(__name__)

# Dynamically resolve absolute paths relative to the project root (/app in Docker)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_PATH = os.path.join(BASE_DIR, "data", "historical_trades.csv")
ARTIFACT_DIR = os.path.join(BASE_DIR, "artifacts")

def train_pipeline(contamination: float = 0.05):
    """
    Enterprise training pipeline for the TBML Isolation Forest.
    """
    logger.info("Initializing model training pipeline...")
    os.makedirs(ARTIFACT_DIR, exist_ok=True)

    try:
        # 1. Ingest Data
        logger.info(f"Loading historical transaction data from {DATA_PATH}")
        if not os.path.exists(DATA_PATH):
            raise FileNotFoundError(f"Missing dataset at {DATA_PATH}. Run generate_mock_data.py first.")
            
        raw_data = pd.read_csv(DATA_PATH) 
        
        # 2. Feature Engineering
        logger.info("Applying feature engineering...")
        processed_data = engineer_features(raw_data)
        
        features = get_feature_columns()
        X = processed_data[features]
        
        # 3. Scaling
        logger.info("Scaling features...")
        scaler = StandardScaler()
        X_scaled = scaler.fit_transform(X)
        
        # 4. Model Training
        logger.info(f"Training Isolation Forest with contamination={contamination}...")
        model = IsolationForest(
            n_estimators=200,
            max_samples='auto',
            contamination=contamination,
            random_state=42,
            n_jobs=-1 
        )
        model.fit(X_scaled)
        
        # 5. Save Artifacts
        model_path = os.path.join(ARTIFACT_DIR, "isolation_forest.joblib")
        scaler_path = os.path.join(ARTIFACT_DIR, "scaler.joblib")
        
        joblib.dump(model, model_path)
        joblib.dump(scaler, scaler_path)
        logger.info(f"Training complete. Artifacts saved to {ARTIFACT_DIR}/")

    except Exception as e:
        logger.critical(f"Pipeline failed during training: {str(e)}")
        raise

if __name__ == "__main__":
    train_pipeline()