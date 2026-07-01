import uuid
from datetime import datetime
from typing import List, Optional
from sqlalchemy import String, Float, Integer, ForeignKey, DateTime, text, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship
from core.database import Base

class Client(Base):
    __tablename__ = "clients"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    company_name: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    historical_risk_score: Mapped[float] = mapped_column(Float, default=0.1) # Safe default low-risk
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # Relationship back-reference to client transactions
    transactions: Mapped[List["TradeTransaction"]] = relationship("TradeTransaction", back_populates="client")

class Commodity(Base):
    __tablename__ = "commodities"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    commodity_code: Mapped[str] = mapped_column(String(50), nullable=False, unique=True) # e.g., 'BRNT_OIL', 'WHEAT'
    display_name: Mapped[str] = mapped_column(String(100), nullable=False)
    current_market_price: Mapped[float] = mapped_column(Float, nullable=False)
    last_updated: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Explicit index for rapid market matching engine lookups
    __table_args__ = (Index("idx_commodity_code", "commodity_code"),)

class TradeTransaction(Base):
    __tablename__ = "trade_transactions"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    transaction_id: Mapped[str] = mapped_column(String(100), nullable=False, unique=True) # TXN-INV-XXXX
    client_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("clients.id"), nullable=False)
    commodity_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("commodities.id"), nullable=False)
    
    invoice_price: Mapped[float] = mapped_column(Float, nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    price_variance_pct: Mapped[float] = mapped_column(Float, nullable=False)
    risk_score: Mapped[float] = mapped_column(Float, nullable=False)
    
    # Core state machine status for Straight-Through Processing (STP)
    status: Mapped[str] = mapped_column(String(50), default="PENDING_VALIDATION") # AUTO_APPROVED_STP, FLAGGED_FOR_REVIEW
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # Relationships
    client: Mapped["Client"] = relationship("Client", back_populates="transactions")
    commodity: Mapped["Commodity"] = relationship("Commodity")

    __table_args__ = (
        Index("idx_txn_status", "status"),
        Index("idx_txn_id", "transaction_id"),
    )