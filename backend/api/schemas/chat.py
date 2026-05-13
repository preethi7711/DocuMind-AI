"""
DocuMind AI — Chat Schemas
============================
WHY WE NEED THESE:
    A robust RAG chat isn't just returning a string.
    We must return the answer AND the citations so the user can verify the AI's claims.
"""

from typing import List, Optional
from pydantic import BaseModel, Field

class ChatMessage(BaseModel):
    """A single message in the conversation history."""
    role: str = Field(description="'user' or 'assistant'")
    content: str

class Citation(BaseModel):
    """Tracks exactly where the AI got its information."""
    document_id: str
    chunk_id: str
    text_snippet: str
    heading: str = "Unknown Section"
    page_number: int = 1

class ChatRequest(BaseModel):
    """Incoming query from the frontend."""
    document_id: str
    messages: List[ChatMessage]
    stream: bool = False
    debug: bool = False  # Set to True to receive retrieval traces

class ChatResponse(BaseModel):
    """Structured response from our RAG pipeline."""
    answer: str
    citations: List[Citation] = []
    trace: Optional[dict] = None  # Contains debug information if requested
