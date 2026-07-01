import os
import joblib
import pandas as pd
from typing import Dict, Any, Tuple
from .utils import setup_logger, engineer_features, get_feature_columns

logger = setup_logger(__name__)

# Dynamically resolve absolute paths relative to the project root (/app in Docker)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

class TBMLPredictor:
    """
    Real-time inference engine for TBML detection.
    Optimized for single-row evaluations within an API request cycle.
    """
    def __init__(self, artifact_dir: str = "artifacts"):
        self.model_path = os.path.join(BASE_DIR, artifact_dir, "isolation_forest.joblib")
        self.scaler_path = os.path.join(BASE_DIR, artifact_dir, "scaler.joblib")
        self.model = None
        self.scaler = None

    def load_artifacts(self) -> None:
        """Loads the pre-trained model and scaler into memory."""
        try:
            self.model = joblib.load(self.model_path)
            self.scaler = joblib.load(self.scaler_path)
            logger.info("ML inference artifacts loaded successfully.")
        except FileNotFoundError:
            logger.error(f"Artifacts not found at {self.model_path}. You must run train.py first.")
            raise RuntimeError("Model artifacts missing.")

    def predict(self, transaction: Dict[str, Any]) -> Tuple[bool, float]:
        """
        Evaluates a single transaction dictionary.
        Returns: (is_anomalous: bool, risk_score: float)
        """
        if self.model is None or self.scaler is None:
            self.load_artifacts()
            
        try:
            # 1. Convert Dict to DataFrame for consistent processing
            df = pd.DataFrame([transaction])
            
            # 2. Apply the EXACT same feature engineering used in training
            processed_df = engineer_features(df)
            X = processed_df[get_feature_columns()]
            
            # 3. Scale input
            X_scaled = self.scaler.transform(X)
            
            # 4. Predict (-1 is anomaly, 1 is normal)
            prediction = self.model.predict(X_scaled)[0]
            raw_score = self.model.decision_function(X_scaled)[0]
            
            # Map raw score to a 0-100 Operations Dashboard Risk Score
            risk_score = min(max(((0.5 - raw_score) * 100), 0), 100)
            is_anomalous = bool(prediction == -1)
            
            # 5. Hybrid Hard-Rule Override (From your architecture diagram)
            variance = processed_df['price_variance_pct'].iloc[0]
            if variance > 15.0:
                is_anomalous = True
                logger.warning(f"Hard rule triggered: Variance {variance:.2f}% exceeds 15% safety threshold.")
            
            return is_anomalous, risk_score

        except Exception as e:
            logger.error(f"Inference failure: {str(e)}")
            raise