import uuid
from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional

class TransactionResponse(BaseModel):
    """Schema for the API response after processing an LC."""
    id: uuid.UUID
    transaction_id: str
    client_name: str
    commodity_code: str
    invoice_price: float
    market_price: float
    quantity: int
    price_variance_pct: float
    risk_score: float
    status: str
    created_at: datetime

    class Config:
        from_attributes = True  # Allows Pydantic to read directly from SQLAlchemy models