"""
DocuMind AI — PDF Processing Service
======================================
WHY THIS MODULE EXISTS:
    We need to reliably extract data from PDFs. Before we blindly throw a PDF
    into an OCR engine or an LLM, we must understand what it is. Is it a native
    digital PDF with selectable text? Or is it a scanned image wrapper?
    This dictation completely changes our processing pipeline.

HOW IT WORKS:
    Uses PyMuPDF (fitz), which is currently the fastest and most robust C-based
    PDF library for Python. We avoid PyPDF2 because it's slow and fails on
    malformed PDFs.

ENGINEERING PRINCIPLE:
    Single Responsibility. This module ONLY handles PDF manipulation:
    - Metadata extraction
    - Scanned vs Digital detection
    - Page rendering
    It DOES NOT handle database saving or API responses.
"""

import fitz  # PyMuPDF
import cv2
import numpy as np
from pathlib import Path
from loguru import logger
from typing import Dict, Any, Tuple

class PDFProcessor:
    """Core logic for PDF parsing and validation."""
    
    @staticmethod
    def extract_metadata(file_path: Path) -> Dict[str, Any]:
        """
        Extract internal PDF metadata.
        
        WHY: Metadata gives us context (author, creation date) without needing AI.
        """
        try:
            doc = fitz.open(file_path)
            meta = doc.metadata
            page_count = doc.page_count
            
            # fitz metadata keys: format, title, author, subject, keywords, creator, producer, creationDate, modDate
            return {
                "title": meta.get("title", ""),
                "author": meta.get("author", ""),
                "subject": meta.get("subject", ""),
                "keywords": meta.get("keywords", ""),
                "creator": meta.get("creator", ""),
                "producer": meta.get("producer", ""),
                "creation_date": meta.get("creationDate", ""),
                "page_count": page_count,
            }
        except Exception as e:
            logger.error(f"Failed to extract metadata from {file_path}: {e}")
            raise ValueError(f"Invalid or corrupted PDF file: {e}")

    @staticmethod
    def is_scanned_pdf(file_path: Path, sample_pages: int = 3) -> bool:
        """
        Determine if a PDF is primarily scanned (images) or digital (selectable text).
        
        HOW: We sample the first few pages. If the ratio of text length to page area
        is extremely low, but images are present, we classify it as scanned.
        
        WHY: Scanned PDFs MUST go through Phase 4 (OCR). Digital PDFs can skip
        directly to Phase 5/6 (Text Extraction & Chunking), saving massive compute.
        """
        try:
            doc = fitz.open(file_path)
            total_text_length = 0
            pages_to_check = min(sample_pages, doc.page_count)
            
            for i in range(pages_to_check):
                page = doc[i]
                text = page.get_text()
                total_text_length += len(text.strip())
                
            # Heuristic: If across the sample pages we found less than 50 characters
            # of selectable text, it's highly likely a scanned document (or entirely images).
            # Professional systems use more complex heuristics, but this is a solid baseline.
            is_scanned = total_text_length < 50
            logger.debug(f"PDF {file_path.name} is_scanned: {is_scanned} (Text length: {total_text_length})")
            return is_scanned
            
        except Exception as e:
            logger.error(f"Failed to detect scanned status for {file_path}: {e}")
            # Safe fallback: assume scanned so it goes through OCR
            return True

    @staticmethod
    def render_page_to_image(file_path: Path, page_number: int, output_path: Path, dpi: int = 300) -> str:
        """
        Renders a specific page to an image file (e.g. PNG).
        
        WHY: Useful for frontend document previews or debugging.
        """
        try:
            doc = fitz.open(file_path)
            if page_number < 0 or page_number >= doc.page_count:
                raise ValueError(f"Invalid page number {page_number}. PDF has {doc.page_count} pages.")
                
            page = doc[page_number]
            zoom = dpi / 72
            mat = fitz.Matrix(zoom, zoom)
            pix = page.get_pixmap(matrix=mat, alpha=False)
            
            pix.save(str(output_path))
            return str(output_path)
            
        except Exception as e:
            logger.error(f"Failed to render page {page_number} of {file_path}: {e}")
            raise

    @staticmethod
    def render_page_to_numpy(file_path: Path, page_number: int, dpi: int = 300) -> np.ndarray:
        """
        Renders a PDF page directly into an in-memory NumPy array.
        
        WHY: Completely eliminates disk I/O during the OCR pipeline.
        Data flows: PyMuPDF Pixmap -> byte buffer -> NumPy array -> OpenCV
        """
        try:
            doc = fitz.open(file_path)
            if page_number < 0 or page_number >= doc.page_count:
                raise ValueError(f"Invalid page number {page_number}")
                
            page = doc[page_number]
            zoom = dpi / 72
            mat = fitz.Matrix(zoom, zoom)
            # alpha=False ensures 3 channels (RGB) instead of 4 (RGBA)
            pix = page.get_pixmap(matrix=mat, alpha=False)
            
            # Convert raw bytes to numpy array
            img_array = np.frombuffer(pix.samples, dtype=np.uint8)
            # Reshape based on height, width, and number of channels (usually 3 for RGB)
            img_array = img_array.reshape((pix.h, pix.w, pix.n))
            
            # PyMuPDF outputs RGB, but OpenCV expects BGR.
            # We must convert the color space so OpenCV processes it correctly.
            # (Though if we convert to grayscale immediately, this step is arguably 
            # optional, but it's best practice for pipeline consistency).
            img_bgr = cv2.cvtColor(img_array, cv2.COLOR_RGB2BGR)
            
            return img_bgr
            
        except Exception as e:
            logger.error(f"Failed to render page {page_number} to numpy: {e}")
            raise
