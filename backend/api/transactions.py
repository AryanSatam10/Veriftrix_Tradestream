import os
import shutil
import logging
from fastapi import APIRouter, UploadFile, File, Form, Depends, HTTPException, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

# Import core services and DB
from core.database import get_db_session
from core.models import TradeTransaction, Client, Commodity
from services.ocr_service import OCRExtractor
from services.market_data import MarketDataIngestionService
from ml_engine.predict import TBMLPredictor
from schemas.transaction import TransactionResponse

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/transactions", tags=["Transactions"])

# Initialize singletons for stateless services
ocr_service = OCRExtractor()
market_service = MarketDataIngestionService()
ml_detector = TBMLPredictor()

UPLOAD_DIR = "temp_uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

@router.post("/process-lc", response_model=TransactionResponse, status_code=201)
async def process_letter_of_credit(
    background_tasks: BackgroundTasks,
    client_name: str = Form(..., description="The name of the corporate client submitting the LC"),
    commodity_code: str = Form(..., description="The ticker/code for the traded goods (e.g., BRNT_OIL)"),
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db_session)
):
    """
    Enterprise Endpoint for Straight-Through Processing (STP) of Letters of Credit.
    """
    if not file.filename.endswith('.pdf'):
        raise HTTPException(status_code=400, detail="Invalid file type. Only PDF is supported.")

    file_path = os.path.join(UPLOAD_DIR, file.filename)
    
    try:
        # 1. Stream file to disk (Prevents RAM overflow for large PDFs)
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
            
        # 2. Run OCR Extraction
        logger.info(f"Initiating OCR for {file.filename}")
        extracted_data = ocr_service.process_document(file_path)
        
        # 3. Ensure Client Exists (or mock fetch for this example)
        client_query = await db.execute(select(Client).where(Client.company_name == client_name))
        client = client_query.scalar_one_or_none()
        if not client:
            # Auto-onboard client for demonstration (in prod, raise 404)
            client = Client(company_name=client_name, historical_risk_score=0.1)
            db.add(client)
            await db.flush() # Flush to get the client ID without committing

        # 4. Sync Market Data & Fetch Commodity
        logger.info(f"Syncing live market data for {commodity_code}")
        await market_service.update_internal_price_index(db, commodity_code)
        
        commodity_query = await db.execute(select(Commodity).where(Commodity.commodity_code == commodity_code))
        commodity = commodity_query.scalar_one()

        # 5. Prepare ML Payload & Execute Anomaly Detection
        variance_pct = abs((extracted_data["amount"] - commodity.current_market_price) / commodity.current_market_price) * 100
        
        ml_payload = {
            "invoice_price": extracted_data["amount"],
            "market_price": commodity.current_market_price,
            "quantity": extracted_data["quantity"],
            "client_historical_risk": client.historical_risk_score,
            "price_variance_pct": variance_pct
        }
        
        logger.info("Executing Isolation Forest TBML evaluation")
        is_anomalous, risk_score = ml_detector.predict(ml_payload)
        status = "FLAGGED_FOR_REVIEW" if is_anomalous else "AUTO_APPROVED_STP"

        # 6. Persist Complete Transaction Record to PostgreSQL
        transaction = TradeTransaction(
            transaction_id=f"TXN-{extracted_data['invoice_number']}",
            client_id=client.id,
            commodity_id=commodity.id,
            invoice_price=extracted_data["amount"],
            quantity=extracted_data["quantity"],
            price_variance_pct=variance_pct,
            risk_score=risk_score,
            status=status
        )
        db.add(transaction)
        
        # We don't need to call await db.commit() here because our get_db_session 
        # dependency automatically commits on a successful yield!
        
        logger.info(f"Transaction {transaction.transaction_id} processed successfully. Status: {status}")
        
        # Construct response
        return TransactionResponse(
            id=transaction.id,
            transaction_id=transaction.transaction_id,
            client_name=client.company_name,
            commodity_code=commodity.commodity_code,
            invoice_price=transaction.invoice_price,
            market_price=commodity.current_market_price,
            quantity=transaction.quantity,
            price_variance_pct=variance_pct,
            risk_score=transaction.risk_score,
            status=transaction.status,
            created_at=transaction.created_at
        )

    except ValueError as ve:
        logger.error(f"Validation error during processing: {str(ve)}")
        raise HTTPException(status_code=422, detail=str(ve))
    except Exception as e:
        logger.critical(f"System failure during transaction processing: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal core processing failure.")
    finally:
        # Background task cleans up the file after the response is sent
        background_tasks.add_task(cleanup_file, file_path)

def cleanup_file(path: str):
    """Utility to remove temporary files."""
    if os.path.exists(path):
        os.remove(path)
        logger.info(f"Cleaned up temporary file: {path}")