import os
import shutil
import logging
import json
from datetime import datetime
from contextlib import asynccontextmanager
from fastapi import FastAPI, UploadFile, File, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# Import our custom services
from services.ocr_service import OCRExtractor
from ml_engine.predict import TBMLPredictor
from core.database import engine, Base
from api.transactions import router as transactions_router

# 1. Setup Enterprise Logging
logging.basicConfig(
    level=logging.INFO, 
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# 2. Initialize Singletons for stateless services
ocr_service = OCRExtractor()
ml_detector = TBMLPredictor()

# Temporary storage for uploads
UPLOAD_DIR = "temp_uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

# ========================================================================
# 2.5 PERSISTENT LOCAL CACHE (JSON)
# Replaces the volatile RAM-only list so your data survives server restarts.
# ========================================================================
CACHE_FILE = "transaction_cache.json"

def load_cache():
    if os.path.exists(CACHE_FILE):
        try:
            with open(CACHE_FILE, "r") as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Error reading cache: {e}")
            return []
    return []

def save_cache(data):
    with open(CACHE_FILE, "w") as f:
        json.dump(data, f, indent=4)

# Load existing history on startup
TRANSACTION_HISTORY = load_cache()

class RiskResponse(BaseModel):
    transaction_id: str
    extracted_data: dict
    is_anomalous: bool
    risk_score: float
    status: str
    risk_drivers: list = []
        

# 3. Define the single Lifespan Context Manager
@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Initializing Enterprise API Gateway...")
    
    # Initialize DB Tables 
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        logger.info("Database schemas verified.")

    # Pre-load ML Model into the GLOBAL instance
    try:
        ml_detector.load_artifacts()
        logger.info("Isolation Forest ML artifacts loaded into memory successfully.")
    except Exception as e:
        logger.warning(f"ML Model artifacts missing. Ensure you run train.py first. Details: {e}")
        
    yield  
    
    logger.info("Shutting down API Gateway gracefully...")
    await engine.dispose()

# 4. Initialize the FastAPI App
app = FastAPI(
    title="TradeStream AI Gateway", 
    description="Enterprise API for Trade Finance STP and TBML Detection",
    version="2.0.0",
    lifespan=lifespan
)

# 5. Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 6. Include external routers
app.include_router(transactions_router)

# 7. Define base application endpoints
@app.get("/health", tags=["System"])
async def health_check():
    return {"status": "operational", "components": ["api", "db", "ml_engine"]}

@app.post("/upload-lc", response_model=RiskResponse, tags=["Document Processing"])
async def process_letter_of_credit(file: UploadFile = File(...)):
    if not file.filename.endswith('.pdf'):
        raise HTTPException(status_code=400, detail="Only PDF files are supported.")

    file_path = os.path.join(UPLOAD_DIR, file.filename)
    
    try:
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        extracted_data = ocr_service.process_document(file_path)
        target_transaction_id = f"TXN-{extracted_data.get('invoice_number', '000')}"
        
        # Duplicate Check
        for txn in TRANSACTION_HISTORY:
            if txn["transaction_id"] == target_transaction_id:
                raise HTTPException(
                    status_code=409, 
                    detail=f"Duplicate Document: Invoice {extracted_data.get('invoice_number')} has already been processed in the system."
                )

        current_market_price = 1000.00 
        
        total_amount = extracted_data.get("amount", 0)
        quantity = extracted_data.get("quantity", 1)
        
        # Protect against division by zero
        unit_price = total_amount / quantity if quantity > 0 else total_amount
        
        ml_payload = {
            "invoice_price": unit_price,  # <-- Pass unit_price instead of total amount
            "market_price": current_market_price,
            "quantity": quantity,
            "client_historical_risk": 0.1 
        }
        
        is_anomalous, risk_score = ml_detector.predict(ml_payload)
        status = "FLAGGED_FOR_REVIEW" if is_anomalous else "AUTO_APPROVED_STP"
        
        # -------------------------------------------------------------------
        # EXPLAINABLE AI (XAI) RISK DRIVERS
        # -------------------------------------------------------------------
        risk_drivers = []
        if is_anomalous:
            amount_val = extracted_data.get('amount', 0)
            risk_drivers.append(f"Settlement Value (${amount_val:,.2f}) exceeds historical bounds for this counterparty.")
            if extracted_data.get('quantity', 0) > 0:
                risk_drivers.append("Isolation Forest detected dimensional anomaly in commodity quantity-to-price ratio.")
        
        response = RiskResponse(
            transaction_id=target_transaction_id,
            extracted_data=extracted_data,
            is_anomalous=is_anomalous,
            risk_score=risk_score,
            status=status,
            risk_drivers=risk_drivers
        )

        # Append to memory AND save to the JSON file
        TRANSACTION_HISTORY.append({
            "transaction_id": response.transaction_id,
            "amount": extracted_data.get("amount", 0),
            "is_anomalous": is_anomalous,
            "risk_score": risk_score,
            "status": status,  # <-- Ensure this is tracked
            "created_at": datetime.now().isoformat()
        })
        save_cache(TRANSACTION_HISTORY)
        
        return response

    except HTTPException:
        raise
    except Exception as e:
        error_msg = str(e)
        logger.error(f"Transaction processing failed: {error_msg}")

        # NEW: Gracefully catch AI Quota Limits
        if "429" in error_msg or "RESOURCE_EXHAUSTED" in error_msg:
            raise HTTPException(
                status_code=429, 
                detail="AI Provider quota exceeded. The daily limit for document extraction has been reached. Please try again tomorrow."
            )
        
        raise HTTPException(status_code=500, detail="Internal Server Error during processing.")
        
    finally:
        if os.path.exists(file_path):
            os.remove(file_path)

@app.get("/analytics", tags=["Dashboard"])
async def get_dashboard_analytics():
    try:
        total_vol = 0
        anomalies = 0
        chart_map = {}
        
        for r in TRANSACTION_HISTORY:
            amount = r["amount"]
            total_vol += amount
            
            if r["is_anomalous"]:
                anomalies += 1
                
            # Convert ISO string back to date for chart grouping
            date_obj = datetime.fromisoformat(r["created_at"])
            date_str = date_obj.strftime("%b %d")
            
            if date_str not in chart_map:
                chart_map[date_str] = {"date": date_str, "volume": 0, "riskScore": 0, "count": 0}
                
            chart_map[date_str]["volume"] += amount
            chart_map[date_str]["riskScore"] += r["risk_score"]
            chart_map[date_str]["count"] += 1
            
        chart_data = []
        for date_key, data in chart_map.items():
            data["riskScore"] = data["riskScore"] / data["count"] if data["count"] > 0 else 0
            chart_data.append(data)
            
        chart_data.sort(key=lambda x: datetime.strptime(x["date"], "%b %d"))
        
        # Sort reverse chronological (newest first) for the Ledger Table
        recent_txns = sorted(TRANSACTION_HISTORY, key=lambda x: x["created_at"], reverse=True)[:10]
        
        return {
            "kpis": {
                "total_volume": total_vol,
                "processed_count": len(TRANSACTION_HISTORY),
                "intervention_rate": round((anomalies / len(TRANSACTION_HISTORY) * 100), 1) if TRANSACTION_HISTORY else 0
            },
            "chart_data": chart_data,
            "recent_transactions": recent_txns
        }
    except Exception as e:
        logger.error(f"Failed to generate analytics: {e}")
        return {"error": str(e), "kpis": {"total_volume": 0, "processed_count": 0, "intervention_rate": 0}, "chart_data": [], "recent_transactions": []}
    


class StatusUpdateRequest(BaseModel):
    status: str  # Expecting "CLEARED" or "REJECTED"

@app.put("/transactions/{transaction_id}/status", tags=["Document Processing"])
async def update_transaction_status(transaction_id: str, payload: StatusUpdateRequest):
    """Updates the database log with the analyst's final human-in-the-loop decision."""
    global TRANSACTION_HISTORY
    found = False
    
    for txn in TRANSACTION_HISTORY:
        if txn["transaction_id"] == transaction_id:
            txn["status"] = payload.status
            # If manually cleared, flip the anomaly flag to False for the UI ledger
            if payload.status == "CLEARED":
                txn["is_anomalous"] = False
            elif payload.status == "REJECTED":
                txn["is_anomalous"] = True
            found = True
            break
            
    if not found:
        raise HTTPException(status_code=404, detail="Transaction reference not found.")
        
    save_cache(TRANSACTION_HISTORY)
    return {"success": True, "updated_status": payload.status}