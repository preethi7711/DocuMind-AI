"""
DocuMind AI — OCR API Routes
==============================
WHY SEPARATE ROUTES?
    While the document upload route handles the initial file ingestion,
    the OCR processing might take minutes. It should be a separate endpoint
    that clients can trigger (and later, poll or receive webhooks from).
"""

from fastapi import APIRouter, HTTPException, BackgroundTasks, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from pathlib import Path

from backend.api.schemas.responses import SuccessResponse
from backend.api.schemas.ocr import OCRDocument
from backend.services.ocr_service import OCRService
from backend.database.session import get_db
from backend.config.settings import settings

router = APIRouter(
    prefix="/ocr",
    tags=["OCR Extraction"],
)

@router.post(
    "/process/{document_id}",
    response_model=SuccessResponse[OCRDocument],
    summary="Run OCR Pipeline",
    description="Executes the full in-memory OCR extraction pipeline for a given document.",
)
async def process_document_ocr(
    document_id: str,
    db: AsyncSession = Depends(get_db)
) -> SuccessResponse[OCRDocument]:
    """
    Phase 4 — Trigger OCR Pipeline
    
    In a true production environment, this would push a message to RabbitMQ/Redis
    and return an immediate 'Processing' status. For now, it runs synchronously
    to prove the pipeline works end-to-end.
    """
    # 1. Find the document in the database
    from backend.database.models import Document
    from sqlalchemy import select
    
    result = await db.execute(select(Document).where(Document.id == document_id))
    db_doc = result.scalar_one_or_none()
            
    if not db_doc:
        raise HTTPException(status_code=404, detail="Document not found")

    target_file = Path(db_doc.file_path)
    if not target_file.exists():
        raise HTTPException(status_code=404, detail="Source file not found on disk")

    # 2. Update status to 'processing'
    db_doc.status = "processing"
    await db.flush()

    try:
        # Run the Service Layer in a thread pool to avoid blocking the event loop
        from fastapi.concurrency import run_in_threadpool
        ocr_document = await run_in_threadpool(OCRService.process_pdf, target_file, document_id)
        
        # 3. Update status to 'completed'
        db_doc.status = "completed"
        await db.commit()
        
        return SuccessResponse(
            success=True,
            message="OCR Extraction completed successfully",
            data=ocr_document
        )
    except Exception as e:
        db_doc.status = "error"
        await db.commit()
        raise HTTPException(status_code=500, detail=f"OCR processing failed: {str(e)}")
