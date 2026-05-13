"""
DocuMind AI — Document Routes
==============================
WHY THIS ROUTE?
    This is the primary entry point for the system. Users upload PDFs here,
    which triggers the entire background ingestion pipeline (OCR -> Layout -> Embedding).
"""

from fastapi import APIRouter, UploadFile, File, HTTPException, Depends, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from backend.api.schemas.responses import SuccessResponse
from backend.api.schemas.documents import DocumentResponseSchema
from backend.services.document_service import DocumentService
from backend.services.ingestion_service import IngestionService
from backend.database.session import get_db, async_session_factory
from backend.database.models import Document
from backend.config.settings import settings

router = APIRouter(
    prefix="/documents",
    tags=["Documents"],
)

async def _run_background_ingestion(document_id: str):
    """
    Helper to run the full ingestion pipeline in the background.
    We create a fresh database session since the request session will be closed.
    """
    async with async_session_factory() as db:
        await IngestionService.process_document(document_id, db)

@router.post(
    "/upload",
    response_model=SuccessResponse[DocumentResponseSchema],
    summary="Upload Document",
    description="Upload a PDF document. Extracts metadata and triggers the background processing pipeline.",
)
async def upload_document(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db)
) -> SuccessResponse[DocumentResponseSchema]:
    """
    Phase 2 — PDF Upload Endpoint
    """
    # 1. Basic Validation
    if not file.filename:
        raise HTTPException(status_code=400, detail="Filename missing")
    
    ext = file.filename.split(".")[-1].lower()
    if ext not in settings.allowed_extensions_list:
        raise HTTPException(
            status_code=400, 
            detail=f"Invalid file type. Allowed: {settings.allowed_extensions}"
        )
    
    try:
        # 2. Save file and create DB record
        document_schema = await DocumentService.upload_document(file, db)
        await db.commit() # Commit to persist the record before background task starts
        
        # 3. Trigger Background Processing (OCR -> Embedding)
        background_tasks.add_task(_run_background_ingestion, document_schema.id)
        
        return SuccessResponse(
            success=True,
            message="Document uploaded and processing started in background",
            data=document_schema
        )
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail="Internal server error during upload")

@router.get(
    "/{document_id}",
    response_model=SuccessResponse[DocumentResponseSchema],
    summary="Get Document Details",
    description="Fetches the metadata and status of a specific document from the database.",
)
async def get_document(
    document_id: str,
    db: AsyncSession = Depends(get_db)
) -> SuccessResponse[DocumentResponseSchema]:
    """Phase 2 — Fetch Document Metadata"""
    result = await db.execute(select(Document).where(Document.id == document_id))
    db_doc = result.scalar_one_or_none()
    
    if not db_doc:
        raise HTTPException(status_code=404, detail="Document not found")
        
    return SuccessResponse(
        success=True,
        message="Document found",
        data=DocumentResponseSchema.model_validate(db_doc)
    )

@router.get(
    "/{document_id}/pdf",
    summary="Get Document PDF",
    description="Returns the raw PDF file for viewing in the frontend.",
)
async def get_document_pdf(
    document_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Phase 6 — PDF viewer endpoint"""
    from fastapi.responses import FileResponse
    result = await db.execute(select(Document).where(Document.id == document_id))
    db_doc = result.scalar_one_or_none()
    
    if not db_doc:
        raise HTTPException(status_code=404, detail="Document not found")
        
    return FileResponse(
        path=db_doc.file_path,
        media_type="application/pdf",
        filename=db_doc.filename,
        content_disposition_type="inline" # Inline so it opens in browser iframe
    )

@router.get(
    "",
    response_model=SuccessResponse,
    summary="List Documents",
    description="Lists all uploaded documents with their current processing status.",
)
async def list_documents(db: AsyncSession = Depends(get_db)) -> SuccessResponse:
    """Phase 2 — Document listing endpoint."""
    result = await db.execute(select(Document).order_by(Document.created_at.desc()))
    docs = result.scalars().all()
    
    return SuccessResponse(
        success=True,
        message=f"Found {len(docs)} documents",
        data={
            "documents": [DocumentResponseSchema.model_validate(d) for d in docs],
            "total": len(docs)
        },
    )
