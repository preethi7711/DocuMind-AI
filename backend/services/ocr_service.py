"""
DocuMind AI — OCR Service Orchestrator
=======================================
WHY THIS EXISTS:
    We have an Image Preprocessor and an OCR Engine. We need a conductor
    to orchestrate them perfectly, handling the entire document lifecycle
    without touching the hard drive (in-memory processing).
"""

import fitz  # PyMuPDF
from pathlib import Path
from loguru import logger
from typing import Optional

from backend.ocr.engine import get_ocr_engine
from backend.preprocessing.pdf_processor import PDFProcessor
from backend.preprocessing.image_processor import ImagePreprocessor
from backend.api.schemas.ocr import OCRDocument, OCRPage

class OCRService:
    """Orchestrates the entire end-to-end OCR pipeline for a document."""

    @staticmethod
    def process_pdf(file_path: Path, document_id: str, max_pages: Optional[int] = None) -> OCRDocument:
        """
        Executes the fully in-memory OCR extraction pipeline.
        
        Data Flow:
        1. Open PDF (PyMuPDF)
        2. For each page -> Render to NumPy array
        3. Preprocess NumPy array (OpenCV)
        4. Extract text via PaddleOCR
        5. Map to Pydantic Schemas
        """
        logger.info(f"Starting OCR extraction for document {document_id}")
        
        try:
            doc = fitz.open(file_path)
            total_pages = doc.page_count
            pages_to_process = min(max_pages, total_pages) if max_pages else total_pages
            
            ocr_pages = []
            ocr_engine = get_ocr_engine()
            
            for page_num in range(pages_to_process):
                logger.debug(f"[{document_id}] Processing page {page_num + 1}/{pages_to_process}")
                
                # 1. In-Memory Render (PDF Page -> NumPy Array)
                # We use 300 DPI for high quality OCR
                raw_image_array = PDFProcessor.render_page_to_numpy(file_path, page_num, dpi=300)
                
                # 2. In-Memory Preprocessing (NumPy -> NumPy)
                # deskew, contrast, denoise, sharpen, binarize
                clean_image_array = ImagePreprocessor.process_for_ocr(raw_image_array)
                
                # 3. OCR Inference (NumPy -> Structured Pydantic Page)
                ocr_page = ocr_engine.process_image(clean_image_array, page_num=page_num + 1)
                
                # Phase 5: Dynamic Routing for Handwriting
                from backend.ocr.handwriting_engine import get_handwriting_engine
                hw_engine = get_handwriting_engine()
                
                if hw_engine:
                    for line in ocr_page.lines:
                        # If PaddleOCR is unsure, it might be messy handwriting
                        if line.confidence < 0.85:
                            logger.debug(f"Routing low-confidence box {line.box} to TrOCR...")
                            
                            # Extract the crop from the clean image
                            pad = 5
                            y1 = max(0, line.box.y1 - pad)
                            y2 = min(clean_image_array.shape[0], line.box.y2 + pad)
                            x1 = max(0, line.box.x1 - pad)
                            x2 = min(clean_image_array.shape[1], line.box.x2 + pad)
                            
                            crop = clean_image_array[y1:y2, x1:x2]
                            
                            handwritten_text = hw_engine.process_region(crop)
                            
                            if handwritten_text:
                                logger.debug(f"TrOCR Translated: '{line.text}' -> '{handwritten_text}'")
                                line.text = handwritten_text
                                line.is_handwritten = True
                                # We boost the confidence back up so it isn't discarded by our reranker
                                line.confidence = 0.90 
                else:
                    logger.debug("Handwriting engine unavailable; skipping dynamic routing.")
                            
                ocr_pages.append(ocr_page)
                
            doc.close()
            
            logger.info(f"Successfully completed OCR for document {document_id}")
            
            return OCRDocument(
                document_id=document_id,
                pages=ocr_pages
            )
            
        except Exception as e:
            logger.error(f"OCR Pipeline failed for {document_id}: {e}")
            raise RuntimeError(f"OCR Pipeline failed: {e}")
