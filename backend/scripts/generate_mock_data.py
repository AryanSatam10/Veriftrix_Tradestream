import os
import numpy as np
import pandas as pd
import logging

# Setup Logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def generate_tbml_dataset(num_samples: int = 10000, anomaly_fraction: float = 0.05, output_dir: str = "data"):
    """
    Generates a synthetic dataset of Trade Finance transactions.
    Injects realistic TBML anomalies (over/under invoicing) for the Isolation Forest to learn from.
    """
    logger.info(f"Generating {num_samples} historical trade records...")
    
    # Ensure data directory exists
    os.makedirs(output_dir, exist_ok=True)
    
    np.random.seed(42) # For reproducibility
    
    # Generate Normal Trades (95%)
    normal_samples = int(num_samples * (1 - anomaly_fraction))
    market_prices_normal = np.random.uniform(500, 5000, normal_samples)
    
    # Normal trades have an invoice price very close to the market price (+/- 2%)
    price_variance_normal = np.random.uniform(0.98, 1.02, normal_samples)
    invoice_prices_normal = market_prices_normal * price_variance_normal
    
    quantities_normal = np.random.randint(10, 1000, normal_samples)
    risk_scores_normal = np.random.uniform(0.01, 0.2, normal_samples) # Low historical risk
    
    # Generate Anomalous Trades (5% TBML)
    anomaly_samples = num_samples - normal_samples
    market_prices_anomaly = np.random.uniform(500, 5000, anomaly_samples)
    
    # Anomalous trades have massive variance (Under-invoicing by 30% or Over-invoicing by 50%)
    price_variance_anomaly = np.random.choice([np.random.uniform(0.5, 0.7), np.random.uniform(1.3, 1.8)], anomaly_samples)
    invoice_prices_anomaly = market_prices_anomaly * price_variance_anomaly
    
    quantities_anomaly = np.random.randint(5000, 20000, anomaly_samples) # Unusually high quantities
    risk_scores_anomaly = np.random.uniform(0.6, 0.99, anomaly_samples) # High historical risk
    
    # Combine and Shuffle
    df_normal = pd.DataFrame({
        'invoice_price': invoice_prices_normal,
        'market_price': market_prices_normal,
        'quantity': quantities_normal,
        'client_historical_risk': risk_scores_normal,
        'is_anomaly': 0 # Label (Not used for training IF, but useful for our validation later)
    })
    
    df_anomaly = pd.DataFrame({
        'invoice_price': invoice_prices_anomaly,
        'market_price': market_prices_anomaly,
        'quantity': quantities_anomaly,
        'client_historical_risk': risk_scores_anomaly,
        'is_anomaly': 1
    })
    
    df_final = pd.concat([df_normal, df_anomaly]).sample(frac=1).reset_index(drop=True)
    
    # Save to CSV
    output_path = os.path.join(output_dir, "historical_trades.csv")
    df_final.to_csv(output_path, index=False)
    
    logger.info(f"Dataset successfully generated and saved to {output_path}")
    logger.info(f"Total anomalies injected: {anomaly_samples} ({anomaly_fraction * 100}%)")

if __name__ == "__main__":
    # When executed inside Docker, the working directory is /app
    generate_tbml_dataset()