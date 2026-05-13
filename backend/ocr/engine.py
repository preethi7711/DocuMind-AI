"""
DocuMind AI — OCR Engine
==========================
WHY PADDLEOCR?
    Tesseract is the old standard, but it struggles with complex layouts and
    requires massive preprocessing. PaddleOCR is a modern, deep-learning based
    OCR engine that provides excellent accuracy, orientation detection, and
    multilingual support out-of-the-box.

HOW THIS WORKS:
    This engine follows a Singleton pattern (sort of) via a module-level instance.
    Loading OCR models into RAM/VRAM takes time. We instantiate it once at startup,
    and then reuse the instance for all incoming requests.

ENGINEERING PRINCIPLE:
    Stateless processing. We feed it a NumPy array (image) and get back structured
    Pydantic objects. No disk I/O is performed here.
"""

import numpy as np
from loguru import logger
from typing import List, Any

from backend.config.settings import settings
from backend.api.schemas.ocr import OCRLine, BoundingBox, OCRPage

class OCREngine:
    """Wrapper for PaddleOCR to handle text extraction and schema formatting."""

    def __init__(self):
        """
        Initializes the PaddleOCR model.
        This is a heavy operation; it downloads weights on first run and loads them into memory.
        """
        from paddleocr import PaddleOCR
        logger.info(f"Initializing PaddleOCR (Lang: {settings.ocr_language}, GPU: {settings.ocr_use_gpu})...")
        try:
            self.model = PaddleOCR(
                use_angle_cls=True,        # Automatically corrects upside-down or sideways text
                lang=settings.ocr_language, # e.g., 'en', 'fr', 'ch'
                use_gpu=settings.ocr_use_gpu,
                show_log=False              # Suppress Paddle's extremely verbose C++ logs
            )
            logger.info("PaddleOCR initialized successfully.")
        except Exception as e:
            logger.error(f"Failed to initialize PaddleOCR: {e}")
            raise RuntimeError(f"OCR Engine initialization failed: {e}")

    def process_image(self, image_array: np.ndarray, page_num: int = 1) -> OCRPage:
        """
        Extracts text from an in-memory NumPy array image.
        
        Args:
            image_array: Preprocessed image matrix (from OpenCV)
            page_num: Page number for tracking
            
        Returns:
            OCRPage: Structured object containing all lines, boxes, and confidence scores.
        """
        if image_array is None or image_array.size == 0:
            logger.warning(f"Empty image array provided for page {page_num}")
            return OCRPage(page_number=page_num, lines=[])

        try:
            # Run inference
            # PaddleOCR returns a nested list. Example format:
            # [[[[10, 10], [100, 10], [100, 30], [10, 30]], ('Text', 0.98)], ...]
            result = self.model.ocr(image_array, cls=True)
            
            # PaddleOCR can return [None] if no text is found, or an empty list
            if not result or not result[0]:
                return OCRPage(page_number=page_num, lines=[])

            lines: List[OCRLine] = []
            
            # result[0] contains the actual text blocks for this image
            for block in result[0]:
                box_points, (text, confidence) = block
                
                # box_points is [[x1,y1], [x2,y1], [x2,y2], [x1,y2]]
                # Convert to flat [x1, y1, x2, y2] bounding box
                x1 = int(min([pt[0] for pt in box_points]))
                y1 = int(min([pt[1] for pt in box_points]))
                x2 = int(max([pt[0] for pt in box_points]))
                y2 = int(max([pt[1] for pt in box_points]))
                
                bbox = BoundingBox(x1=x1, y1=y1, x2=x2, y2=y2)
                
                ocr_line = OCRLine(
                    text=text,
                    confidence=float(confidence),
                    box=bbox
                )
                lines.append(ocr_line)

            return OCRPage(page_number=page_num, lines=lines)
            
        except Exception as e:
            logger.error(f"OCR extraction failed on page {page_num}: {e}")
            raise RuntimeError(f"Failed to extract text: {e}")

# Global instance initialized lazily or at startup
ocr_engine = None

def get_ocr_engine() -> OCREngine:
    """Returns a singleton instance of the OCR Engine."""
    global ocr_engine
    if ocr_engine is None:
        ocr_engine = OCREngine()
    return ocr_engine
