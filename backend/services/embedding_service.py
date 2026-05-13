"""
DocuMind AI — Embedding & Vectorization Service
================================================
WHY THIS EXISTS:
    We need an orchestrator to take a StructuredDocument (from Phase 5),
    chunk it, embed it, and store it in the database.
"""

from loguru import logger

from backend.api.schemas.extraction import StructuredDocument
from backend.embeddings.chunker import ChunkingEngine
from backend.embeddings.embedder import get_embedding_engine
from backend.database.vector_store import get_vector_store
from sqlalchemy.ext.asyncio import AsyncSession

class EmbeddingService:
    """Orchestrates the ingestion of a structured document into the vector database."""

    @staticmethod
    async def process_document(document: StructuredDocument, db: AsyncSession) -> int:
        """
        Executes the chunking and embedding pipeline.
        
        Returns:
            int: The number of chunks successfully embedded and stored.
        """
        logger.info(f"Starting Embedding Pipeline for document: {document.document_id}")
        
        try:
            # 1. Semantic Chunking
            chunks = ChunkingEngine.chunk_document(document)
            if not chunks:
                logger.warning(f"No chunks generated for document {document.document_id}.")
                return 0
                
            # 2. Embedding Generation (Heavy operation - run in thread if needed)
            from fastapi.concurrency import run_in_threadpool
            embedder = get_embedding_engine()
            embeddings = await run_in_threadpool(embedder.embed_chunks, chunks)
            
            # 3. Vector Storage
            vector_store = get_vector_store()
            await run_in_threadpool(vector_store.insert_chunks, chunks, embeddings)
            
            # 4. Relational Storage (Save chunks to SQLite for metadata tracking)
            from backend.database.models import Chunk
            for chunk_data in chunks:
                db_chunk = Chunk(
                    id=chunk_data.chunk_id,
                    document_id=chunk_data.document_id,
                    content=chunk_data.text,
                    page_number=1, # ChunkingEngine doesn't track page_num yet, will fix in Phase 6.1
                    heading=chunk_data.metadata.get("heading"),
                    vector_id=chunk_data.chunk_id
                )
                db.add(db_chunk)
            
            await db.flush()
            
            logger.info(f"Successfully processed and stored {len(chunks)} chunks for {document.document_id}")
            return len(chunks)
            
        except Exception as e:
            logger.error(f"Embedding pipeline failed for {document.document_id}: {e}")
            raise RuntimeError(f"Embedding pipeline failed: {e}")
