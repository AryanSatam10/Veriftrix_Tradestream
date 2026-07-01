import os
import re
import logging
import numpy as np
from typing import Dict, Any
from pydantic import BaseModel, ValidationError

# Heavy Extraction Libraries
from pypdf import PdfReader
from pdf2image import convert_from_path
import camelot
from paddleocr import PaddleOCR

# Configure Enterprise-grade logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class ExtractedInvoiceData(BaseModel):
    invoice_number: str
    amount: float
    goods_description: str
    quantity: int

class OCRExtractor:
    """
    Enterprise Hybrid Document Router.
    Routes digital PDFs to Camelot for flawless grid extraction, 
    and scanned images to PaddleOCR for deep-learning visual extraction.
    """
    
    def __init__(self):
        # Initialize Deep Learning vision model into memory once on boot
        logger.info("Booting PaddleOCR Vision Models (this will take a moment)...")
        self.paddle = PaddleOCR(use_angle_cls=True, lang='en', show_log=False)

    def _is_digital_pdf(self, pdf_path: str) -> bool:
        """Determines if the PDF has an embedded digital text layer."""
        try:
            reader = PdfReader(pdf_path)
            text = ""
            for page in reader.pages:
                text += page.extract_text() or ""
            # If significant text is found digitally, it is not a flat scan
            is_digital = len(text.strip()) > 100
            logger.info(f"PDF Analysis: Digital layer present = {is_digital}")
            return is_digital
        except Exception as e:
            logger.warning(f"Failed to read PDF text layer: {e}")
            return False

    def _extract_via_camelot(self, pdf_path: str) -> str:
        """Extracts text and flawless table grids natively from a digital PDF."""
        logger.info("Routing to Camelot (Digital Extraction)...")
        raw_text = ""
        
        # 1. Grab raw document text
        reader = PdfReader(pdf_path)
        for page in reader.pages:
            raw_text += (page.extract_text() or "") + "\n"
            
        # 2. Reconstruct Tables
        try:
            # Stream flavor handles borderless/invisible tables perfectly
            tables = camelot.read_pdf(pdf_path, pages='all', flavor='stream')
            for i, table in enumerate(tables):
                logger.info(f"Camelot identified table {i+1} with shape {table.df.shape}")
                # Inject perfectly ordered table text back into the string
                raw_text += "\n" + table.df.to_string(index=False, header=False) + "\n"
        except Exception as e:
            logger.warning(f"Camelot table extraction fallback: {e}")
            
        return raw_text

    def _extract_via_paddle(self, pdf_path: str) -> str:
        """Uses Deep Learning to extract text and structure from a scanned image."""
        logger.info("Routing to PaddleOCR (Visual Extraction)...")
        images = convert_from_path(pdf_path, dpi=300)
        
        full_text = ""
        for i, image in enumerate(images):
            # Convert PIL image to OpenCV Numpy array
            img_array = np.array(image)
            
            # Paddle physically maps bounding boxes across the layout
            result = self.paddle.ocr(img_array, cls=True)
            
            if result and result[0]:
                for line in result[0]:
                    # line[1][0] is the text, line[1][1] is the confidence score
                    full_text += line[1][0] + "\n"
                    
        return full_text

    def _parse_to_json(self, raw_text: str) -> Dict[str, Any]:
        """Applies Forced-Boundary Regex to the highly-structured text output."""
        logger.info("Parsing structured text output...")
        
        cleaned = re.sub(r'["\|_]', ' ', raw_text)

        inv_match = re.search(r"Invoice\s*(?:Number|No\.?)[\s:]*([A-Z0-9\-\n\s]+?)(?=\s*(?:Date|Ref))", cleaned, re.IGNORECASE)
        amt_match = re.search(r"(?:Total\s*Amount|Grand\s*Total)[\s:\-\n]*(?:USD|EUR|INR|\$)?[\s\n]*([\d,]+\.\d{2})", cleaned, re.IGNORECASE)
        qty_match = re.search(r"(?:Quantity|Qty)[\s:\n]*([\d,]+)", cleaned, re.IGNORECASE)
        goods_match = re.search(r"Description\s*of\s*Goods[\s:\n]*([A-Za-z0-9\s\,\.\-\n]+?)(?=\s*(?:Quantity|Qty|\$|USD|Unit|Line))", cleaned, re.IGNORECASE)

        def _get_val(match): return match.group(1).strip() if match else "UNKNOWN"
        
        raw_inv = _get_val(inv_match)
        invoice_number = re.sub(r'\s+', '', raw_inv) if raw_inv != "UNKNOWN" else raw_inv

        raw_goods = _get_val(goods_match)
        goods_description = re.sub(r'\s+', ' ', raw_goods).strip() if raw_goods != "UNKNOWN" else raw_goods

        def _clean_number(val: str, is_float: bool = False):
            if val == "UNKNOWN": return 0.0 if is_float else 0
            clean_val = re.sub(r'[^\d\.]', '', val)
            try:
                return float(clean_val) if is_float else int(float(clean_val))
            except ValueError:
                return 0.0 if is_float else 0

        raw_data = {
            "invoice_number": invoice_number,
            "amount": _clean_number(_get_val(amt_match), True),
            "quantity": _clean_number(_get_val(qty_match), False),
            "goods_description": goods_description
        }

        try:
            validated_data = ExtractedInvoiceData(**raw_data)
            logger.info("Data successfully validated through Pydantic schema.")
            return validated_data.model_dump() if hasattr(validated_data, 'model_dump') else validated_data.dict()
        except ValidationError as e:
            logger.error(f"Validation failed: {e.json()}")
            raise ValueError(f"Extracted data did not meet structural requirements: {e.errors()}")

    def process_document(self, pdf_path: str) -> Dict[str, Any]:
        """Orchestrates the Hybrid Routing."""
        logger.info(f"Processing document: {pdf_path}")
        
        if self._is_digital_pdf(pdf_path):
            raw_text = self._extract_via_camelot(pdf_path)
        else:
            raw_text = self._extract_via_paddle(pdf_path)
            
        logger.info(f"\n--- EXTRACTED TEXT START ---\n{raw_text}\n--- EXTRACTED TEXT END ---")
        return self._parse_to_json(raw_text)