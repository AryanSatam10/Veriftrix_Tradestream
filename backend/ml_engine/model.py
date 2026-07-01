import os
import joblib
import logging
import pandas as pd
from typing import Dict, Any, Tuple
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler

# Configure Enterprise-grade logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class TBMLAnomalyDetector:
    """
    Trade-Based Money Laundering (TBML) Anomaly Detection Engine.
    Utilizes Isolation Forest to flag under/over-invoicing and suspicious trade patterns.
    """
    
    def __init__(self, model_dir: str = "artifacts"):
        self.model_dir = model_dir
        self.model_path = os.path.join(self.model_dir, "isolation_forest.joblib")
        self.scaler_path = os.path.join(self.model_dir, "scaler.joblib")
        
        # Initialize model and scaler as None (loaded dynamically)
        self.model = None
        self.scaler = None
        
        # Ensure artifact directory exists
        os.makedirs(self.model_dir, exist_ok=True)

    def _feature_engineering(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Calculates derived features for the model, such as price variance.
        """
        # Calculate strict variance percentage between invoice and market price
        df['price_variance_pct'] = abs((df['invoice_price'] - df['market_price']) / df['market_price']) * 100
        
        # Select features relevant for TBML detection
        features = ['invoice_price', 'market_price', 'price_variance_pct', 'quantity', 'client_historical_risk']
        return df[features]

    def train(self, training_data: pd.DataFrame, contamination: float = 0.05) -> None:
        """
        Trains the Isolation Forest model and saves artifacts.
        """
        logger.info("Starting model training process...")
        try:
            X = self._feature_engineering(training_data)
            
            # Scale features (Critical for distance-based/tree-based algorithms to treat features equally)
            self.scaler = StandardScaler()
            X_scaled = self.scaler.fit_transform(X)
            
            # Initialize Isolation Forest
            # contamination defines the expected proportion of outliers (e.g., 5%)
            self.model = IsolationForest(
                n_estimators=200,
                max_samples='auto',
                contamination=contamination,
                random_state=42,
                n_jobs=-1 # Utilize all CPU cores
            )
            
            self.model.fit(X_scaled)
            
            # Save the trained model and scaler
            joblib.dump(self.model, self.model_path)
            joblib.dump(self.scaler, self.scaler_path)
            
            logger.info(f"Model and scaler successfully saved to {self.model_dir}")
            
        except Exception as e:
            logger.error(f"Error during model training: {str(e)}")
            raise

    def load_model(self) -> None:
        """Loads the pre-trained model and scaler into memory."""
        try:
            self.model = joblib.load(self.model_path)
            self.scaler = joblib.load(self.scaler_path)
            logger.info("Model artifacts loaded successfully.")
        except FileNotFoundError:
            logger.error("Model artifacts not found. Please train the model first.")
            raise

    def predict(self, transaction: Dict[str, Any]) -> Tuple[bool, float]:
        """
        Predicts if a single transaction is an anomaly.
        Returns a tuple: (is_anomalous: bool, risk_score: float)
        """
        if self.model is None or self.scaler is None:
            self.load_model()
            
        try:
            # Convert single dictionary payload into DataFrame
            df = pd.DataFrame([transaction])
            X = self._feature_engineering(df)
            
            # Scale input
            X_scaled = self.scaler.transform(X)
            
            # Predict: -1 for anomalies, 1 for normal data
            prediction = self.model.predict(X_scaled)[0]
            
            # decision_function yields a score; lower/negative means more anomalous
            raw_score = self.model.decision_function(X_scaled)[0]
            
            # Normalize risk score to 0-100 scale for the UI dashboard
            # Note: The mapping here depends on empirical calibration
            risk_score = min(max(((0.5 - raw_score) * 100), 0), 100) 
            
            is_anomalous = True if prediction == -1 else False
            
            # Hybrid Rule + ML logic (Incorporating the diagram's 15% rule)
            variance = X['price_variance_pct'].iloc[0]
            if variance > 15.0:
                is_anomalous = True
                logger.warning(f"Transaction flagged by hard-rule: Variance {variance}% exceeds 15% threshold.")
            
            logger.info(f"Prediction complete. Anomaly: {is_anomalous}, Score: {risk_score:.2f}")
            return is_anomalous, risk_score

        except Exception as e:
            logger.error(f"Error during prediction: {str(e)}")
            raise