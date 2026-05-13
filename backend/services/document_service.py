"""
DocuMind AI — Document Business Logic
=======================================
WHY THIS LAYER EXISTS:
    The "Service Layer" orchestrates business logic. 
    API routes should only handle HTTP validation.
    Database models should only handle DB representation.
    The Service layer connects them:
        Route -> Service -> Processing/Database

    This makes the code testable (you can test the service without HTTP requests)
    and modular.
"""

import uuid
import aiofiles
from pathlib import Path
from datetime import datetime, timezone
from fastapi import UploadFile
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from backend.config.settings import settings
from backend.api.schemas.documents import DocumentResponseSchema, DocumentMetadataSchema
from backend.preprocessing.pdf_processor import PDFProcessor

class DocumentService:
    """Orchestrates document uploads and processing initiation."""

    @staticmethod
    async def upload_document(file: UploadFile, db: AsyncSession) -> DocumentResponseSchema:
        """
        Handles the secure saving of an uploaded PDF and initiates parsing.
        """
        # 1. Generate unique ID
        doc_id = str(uuid.uuid4())
        
        # 2. Sanitize filename
        safe_filename = file.filename.replace(" ", "_") if file.filename else f"unnamed_{doc_id}.pdf"
        file_path = settings.upload_path / f"{doc_id}_{safe_filename}"
        
        logger.info(f"Uploading new document: {safe_filename} -> {doc_id}")
        
        # 3. Async write to disk
        try:
            async with aiofiles.open(file_path, 'wb') as out_file:
                while content := await file.read(1024 * 1024):
                    await out_file.write(content)
        except Exception as e:
            logger.error(f"Failed to save file {file.filename}: {e}")
            raise RuntimeError("File saving failed.")
            
        # 4. Extract PDF Metadata
        try:
            from backend.preprocessing.pdf_processor import PDFProcessor
            from backend.database.models import Document
            
            metadata_dict = PDFProcessor.extract_metadata(file_path)
            is_scanned = PDFProcessor.is_scanned_pdf(file_path)
            
            # Create Database Record
            db_doc = Document(
                id=doc_id,
                filename=safe_filename,
                file_path=str(file_path),
                status="uploaded",
                title=metadata_dict.get("title"),
                author=metadata_dict.get("author"),
                page_count=metadata_dict.get("page_count", 0),
                is_scanned=is_scanned
            )
            
            db.add(db_doc)
            await db.flush() # Get the database state without committing yet
            
            response = DocumentResponseSchema(
                id=db_doc.id,
                filename=db_doc.filename,
                status=db_doc.status,
                created_at=db_doc.created_at,
                title=db_doc.title,
                author=db_doc.author,
                page_count=db_doc.page_count,
                is_scanned=db_doc.is_scanned
            )
            
            return response
            
        except Exception as e:
            logger.error(f"Failed to process PDF {file_path.name}: {e}")
            raise ValueError(f"Invalid PDF file: {e}")
