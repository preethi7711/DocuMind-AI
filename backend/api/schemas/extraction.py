from typing import List
from pydantic import BaseModel, Field
from backend.api.schemas.ocr import BoundingBox, OCRLine, OCRPage

class TextBlock(BaseModel):
    """
    A semantic group of text (e.g., a Paragraph or Heading).
    This is what we actually feed into our RAG chunker later.
    """
    type: str = Field(description="'heading', 'paragraph', or 'table'")
    text: str
    box: BoundingBox
    lines: List[OCRLine] = []

class StructuredPage(BaseModel):
    """A page that has been processed by the Layout Analyzer."""
    page_number: int
    blocks: List[TextBlock] = []
    
    @property
    def full_text(self) -> str:
        return "\n\n".join(block.text for block in self.blocks)

class StructuredDocument(BaseModel):
    """The final structured output ready for Embedding and RAG."""
    document_id: str
    pages: List[StructuredPage] = []
    
    @property
    def full_text(self) -> str:
        return "\n\n".join(page.full_text for page in self.pages)
