import os
import json
import logging
import time
from typing import Dict, Any
from pydantic import BaseModel, ValidationError
from dotenv import load_dotenv

# The Modern Google GenAI SDK
from google import genai
from google.genai import types

# Configure Enterprise-grade logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Strict schema for the extracted data using Pydantic
class ExtractedInvoiceData(BaseModel):
    invoice_number: str
    amount: float
    goods_description: str
    quantity: int

class OCRExtractor:
    """
    Next-Generation Document Extraction Service.
    Utilizes the modern google-genai SDK to natively support AQ. Authorization keys.
    """
    
    def __init__(self):
        load_dotenv()
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            logger.error("CRITICAL: GEMINI_API_KEY environment variable is missing.")
            raise ValueError("GEMINI_API_KEY environment variable is not set.")
            
        # Initialize the modern SDK Client
        self.client = genai.Client(api_key=api_key)

    def process_document(self, pdf_path: str) -> Dict[str, Any]:
        logger.info(f"Initiating Multimodal LLM Extraction for: {pdf_path}")
        uploaded_file = None
        
        try:
            logger.info("Uploading document to GenAI endpoint...")
            uploaded_file = self.client.files.upload(file=pdf_path)
            
            # Allow Google's backend a moment to process the file structure
            time.sleep(3)

            prompt = """
            You are an enterprise financial data extraction system.
            Analyze this commercial invoice and extract the key data points.
            Return ONLY a valid JSON object matching this exact schema:
            {
                "invoice_number": "string (the primary invoice number or ID)",
                "amount": 0.0 (float, the total amount due. Strip all currency symbols and commas. Only return the raw number.),
                "goods_description": "string (A concise, 1-line summary of the items or commodity being billed)",
                "quantity": 0 (integer, the total quantity of items. Strip all commas. Only return the raw number.)
            }
            If a field is completely missing or illegible, use "UNKNOWN" for strings and 0 for numbers.
            """


            logger.info("Executing Semantic Analysis...")
            response = self.client.models.generate_content(
                model='gemini-2.5-flash',
                contents=[uploaded_file, prompt],
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    temperature=0.0  # Zero variance for consistent JSON structure
                )
            )
            
            raw_data = json.loads(response.text)
            logger.info(f"LLM Raw Output: {raw_data}")
            
            validated_data = ExtractedInvoiceData(**raw_data)
            logger.info("Data successfully structured and validated.")
            
            return validated_data.model_dump() if hasattr(validated_data, 'model_dump') else validated_data.dict()

        except Exception as e:
            logger.error(f"GenAI Extraction Pipeline Failed: {str(e)}")
            raise

        finally:
            # Security & Compliance Protocol: Always scrub the file from the cloud
            if uploaded_file:
                try:
                    self.client.files.delete(name=uploaded_file.name)
                    logger.info("Security Protocol: Temporary cloud file purged.")
                except Exception as cleanup_error:
                    logger.warning(f"Failed to purge temporary cloud file: {cleanup_error}")