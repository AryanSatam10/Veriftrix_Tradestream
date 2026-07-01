import os
import shutil
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, UploadFile, File, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# Import our custom services
from services.ocr_service import OCRExtractor
from ml_engine.predict import TBMLPredictor
from core.database import engine, Base
from api.transactions import router as transactions_router

# 1. Setup Enterprise Logging (Once)
logging.basicConfig(
    level=logging.INFO, 
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# 2. Initialize Singletons for stateless services globally
ocr_service = OCRExtractor()
ml_detector = TBMLPredictor()

# Temporary storage for uploads
UPLOAD_DIR = "temp_uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

class RiskResponse(BaseModel):
    transaction_id: str
    extracted_data: dict
    is_anomalous: bool
    risk_score: float
    status: str

# 3. Define the single Lifespan Context Manager
@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Modern FastAPI lifespan manager. Handles DB setup and pre-loading 
    the Isolation Forest ML model into memory to eliminate cold-start latency.
    """
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
        
    yield  # Application serves requests here
    
    # Teardown logic
    logger.info("Shutting down API Gateway gracefully...")
    await engine.dispose()

# 4. Initialize the FastAPI App (Once)
app = FastAPI(
    title="TradeStream AI Gateway", 
    description="Enterprise API for Trade Finance STP and TBML Detection",
    version="2.0.0",
    lifespan=lifespan
)

# 5. Configure CORS (Crucial for connecting to a React or Streamlit frontend)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # In production, restrict this to your exact UI domain
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 6. Include external routers
app.include_router(transactions_router)

# 7. Define base application endpoints
@app.get("/health", tags=["System"])
async def health_check():
    """Load balancer ping endpoint."""
    return {"status": "operational", "components": ["api", "db", "ml_engine"]}

@app.post("/upload-lc", response_model=RiskResponse, tags=["Legacy Upload"])
async def process_letter_of_credit(file: UploadFile = File(...)):
    """
    Standalone endpoint for Operations UI to upload a scanned LC/Invoice.
    Orchestrates OCR extraction and ML Risk Scoring.
    """
    if not file.filename.endswith('.pdf'):
        raise HTTPException(status_code=400, detail="Only PDF files are supported.")

    file_path = os.path.join(UPLOAD_DIR, file.filename)
    
    try:
        # Save file to disk
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        # Run OCR Extraction
        extracted_data = ocr_service.process_document(file_path)
        
        # Fetch current market price (Placeholder)
        current_market_price = 1000.00 
        
        # Prepare payload for ML Engine
        ml_payload = {
            "invoice_price": extracted_data["amount"],
            "market_price": current_market_price,
            "quantity": extracted_data["quantity"],
            "client_historical_risk": 0.1 
        }
        
        # Execute Isolation Forest Anomaly Detection
        is_anomalous, risk_score = ml_detector.predict(ml_payload)
        status = "FLAGGED_FOR_REVIEW" if is_anomalous else "AUTO_APPROVED_STP"
        
        return RiskResponse(
            transaction_id=f"TXN-{extracted_data['invoice_number']}",
            extracted_data=extracted_data,
            is_anomalous=is_anomalous,
            risk_score=risk_score,
            status=status
        )

    except Exception as e:
        logger.error(f"Transaction processing failed: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal Server Error during processing.")
        
    finally:
        # Cleanup temporary file
        if os.path.exists(file_path):
            os.remove(file_path)