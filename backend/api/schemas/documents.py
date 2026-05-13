"""
DocuMind AI — Document Schemas
================================
WHY Pydantic Schemas?
    Pydantic schemas validate inputs and serialize outputs.
    They ensure that API clients always receive exact, typed data.
    If we change the database model, the schema isolates the client
    from those internal changes (DTO pattern - Data Transfer Object).
"""

from pydantic import BaseModel, Field, ConfigDict
from typing import Optional
from datetime import datetime

class DocumentMetadataSchema(BaseModel):
    """Schema for extracted PDF metadata."""
    title: Optional[str] = None
    author: Optional[str] = None
    subject: Optional[str] = None
    keywords: Optional[str] = None
    creator: Optional[str] = None
    producer: Optional[str] = None
    creation_date: Optional[str] = None
    page_count: int = 0
    is_scanned: bool = False

class DocumentResponseSchema(BaseModel):
    """Schema for a document returned via API."""
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)
    
    id: str = Field(..., description="Unique document ID (UUID)")
    filename: str = Field(..., description="Original filename")
    status: str = Field(..., description="Processing status")
    created_at: datetime = Field(..., alias="upload_time")
    
    # We add properties to handle the flat metadata from the DB model
    title: Optional[str] = None
    author: Optional[str] = None
    page_count: int = 0
    is_scanned: bool = False
