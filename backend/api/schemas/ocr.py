"""
DocuMind AI — OCR Data Schemas
================================
WHY THESE SCHEMAS EXIST:
    Raw OCR engines return messy nested lists like:
    [[[10, 10], [100, 10], [100, 30], [10, 30]], ("Hello World", 0.98)]
    
    This is unreadable and fragile. We map this raw output into structured
    Pydantic objects so the rest of the application (Layout Analysis, RAG)
    can interact with clean, typed objects.
"""

from typing import List, Tuple
from pydantic import BaseModel, Field

class BoundingBox(BaseModel):
    """
    Coordinates representing the location of text on a page.
    Format: [x1, y1, x2, y2] (top-left to bottom-right)
    """
    x1: int
    y1: int
    x2: int
    y2: int

class OCRLine(BaseModel):
    """Represents a single line of extracted text."""
    text: str = Field(..., description="The extracted text")
    confidence: float = Field(..., description="OCR engine confidence score (0.0 to 1.0)")
    box: BoundingBox = Field(..., description="Bounding box of the text line")
    is_handwritten: bool = Field(default=False, description="True if routed through handwriting model")

class OCRPage(BaseModel):
    """Represents all extracted text on a single page."""
    page_number: int
    lines: List[OCRLine] = []
    
    @property
    def full_text(self) -> str:
        """Helper to get the entire page text joined by newlines."""
        return "\n".join(line.text for line in self.lines)

class OCRDocument(BaseModel):
    """The final structured output of the OCR pipeline."""
    document_id: str
    pages: List[OCRPage] = []
    
    @property
    def full_text(self) -> str:
        return "\n\n".join(page.full_text for page in self.pages)
