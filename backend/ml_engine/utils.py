import logging
import pandas as pd
from typing import List

def setup_logger(name: str) -> logging.Logger:
    """Standardized logger for the ML engine."""
    logger = logging.getLogger(name)
    if not logger.handlers:
        handler = logging.StreamHandler()
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)
    return logger

def engineer_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    Calculates derived features for TBML detection.
    WARNING: Do not mutate the original dataframe in place.
    """
    processed_df = df.copy()
    
    # Calculate variance percentage safely to avoid DivisionByZero
    processed_df['price_variance_pct'] = processed_df.apply(
        lambda row: abs((row['invoice_price'] - row['market_price']) / row['market_price']) * 100 
        if row['market_price'] > 0 else 0.0,
        axis=1
    )
    
    return processed_df

def get_feature_columns() -> List[str]:
    """Centralized definition of features used by the model."""
    return [
        'invoice_price', 
        'market_price', 
        'price_variance_pct', 
        'quantity', 
        'client_historical_risk'
    ]