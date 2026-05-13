"""
DocuMind AI — Unified Ingestion Orchestrator
==============================================
WHY THIS SERVICE?
    Document ingestion is a multi-stage pipeline:
    1. OCR (if scanned) or Text Extraction (if digital)
    2. Layout Analysis (Structuring)
    3. Semantic Chunking
    4. Vector Embedding
    5. Database Persistence

    Instead of making the API route call 5 different services, this orchestrator
    manages the entire lifecycle. It handles errors and updates the document status.
"""

from pathlib import Path
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi.concurrency import run_in_threadpool

from backend.database.models import Document
from backend.services.ocr_service import OCRService
from backend.extraction.layout_analyzer import LayoutAnalyzer
from backend.services.embedding_service import EmbeddingService

class IngestionService:
    """Orchestrates the end-to-end document processing pipeline."""

    @staticmethod
    async def process_document(document_id: str, db: AsyncSession) -> bool:
        """
        Runs the full ingestion pipeline for a given document ID.
        
        Args:
            document_id: The ID of the document in the database.
            db: The async database session.
            
        Returns:
            bool: True if successful, False otherwise.
        """
        from sqlalchemy import select
        
        # 1. Fetch document from DB
        result = await db.execute(select(Document).where(Document.id == document_id))
        db_doc = result.scalar_one_or_none()
        
        if not db_doc:
            logger.error(f"Cannot process document {document_id}: Not found in database.")
            return False
            
        logger.info(f"Starting unified ingestion for document: {db_doc.filename} ({document_id})")
        db_doc.status = "processing"
        await db.commit()
        
        try:
            file_path = Path(db_doc.file_path)
            
            # 2. Step 1: Extraction (OCR or Digital)
            # For Phase 4, we assume everything goes through OCR for now.
            # In Phase 5+, we'll add digital extraction fallback.
            logger.info(f"[{document_id}] Step 1: Running OCR...")
            ocr_doc = await run_in_threadpool(OCRService.process_pdf, file_path, document_id)
            
            # 3. Step 2: Layout Analysis
            logger.info(f"[{document_id}] Step 2: Analyzing layout...")
            structured_doc = await run_in_threadpool(LayoutAnalyzer.analyze_document, ocr_doc)
            
            # 4. Step 3: Chunking & Embedding
            logger.info(f"[{document_id}] Step 3: Chunking and Embedding...")
            chunk_count = await EmbeddingService.process_document(structured_doc, db)
            
            # 5. Finalize
            db_doc.status = "completed"
            await db.commit()
            logger.info(f"[{document_id}] Ingestion complete. {chunk_count} chunks stored.")
            return True
            
        except Exception as e:
            logger.exception(f"[{document_id}] Ingestion failed: {e}")
            db_doc.status = "error"
            await db.commit()
            return False
