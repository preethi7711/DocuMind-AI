"""
DocuMind AI — Semantic Retriever
==================================
WHY ABSTRACTION?
    We don't call the database directly from the Chat Service. The Retriever
    layer handles generating the embedding for the user's question, searching the DB,
    and formatting the results.
"""

from typing import List, Dict, Any
from loguru import logger

from backend.config.settings import settings
from backend.embeddings.embedder import get_embedding_engine
from backend.database.vector_store import get_vector_store
from backend.api.schemas.chat import Citation

class Retriever:
    """Handles semantic search and context formatting."""

    @staticmethod
    def retrieve_context(query: str, document_id: str, debug: bool = False) -> tuple[str, List[Citation], Dict[str, Any] | None]:
        """
        Embeds the query, searches ChromaDB, and returns the formatted context string
        along with the structured Citations for the frontend.
        If debug is True, also returns a detailed trace for observability.
        """
        logger.info(f"Retrieving context for query: '{query}' in doc {document_id}")
        
        # 1. Embed the Question
        embedder = get_embedding_engine()
        query_embedding = embedder.embed_query(query)
        
        # 2. Search Database
        vector_store = get_vector_store()
        
        # We query ChromaDB and use BM25 to get a robust candidate pool.
        # Phase 3: Hybrid Search Architecture
        initial_k = settings.rag_top_k * 3
        
        from backend.rag.hybrid_search import HybridSearch
        retrieved_ids, retrieved_texts, retrieved_metadatas, retrieved_distances = HybridSearch.search(
            query=query,
            document_id=document_id,
            vector_store=vector_store,
            query_embedding=query_embedding,
            initial_k=initial_k
        )
        
        trace = None
        if debug:
            trace = {
                "original_query": query,
                "vector_search_results": []
            }

        # 3. Process Results
        if not retrieved_ids:
            return "No relevant context found.", [], trace
        # Phase 2: Confidence-Aware Reranking
        from backend.rag.reranker import ConfidenceReranker
        top_chunks, all_scored_chunks = ConfidenceReranker.rerank(
            ids=retrieved_ids,
            texts=retrieved_texts,
            metadatas=retrieved_metadatas,
            distances=retrieved_distances,
            top_k=settings.rag_top_k
        )
        
        context_blocks = []
        citations = []
        
        for i, chunk in enumerate(top_chunks):
            # Phase 4: Inject Uncertainty tags for penalized chunks
            chunk_text = chunk.text
            if chunk.status == "penalized":
                chunk_text = f"<uncertain>\n{chunk_text}\n</uncertain>"

            # Format context block for the LLM
            block = f"--- CHUNK {i+1} ---\nSection: {chunk.heading}\n{chunk_text}\n"
            context_blocks.append(block)
            
            # Build Citation for the user
            citations.append(Citation(
                document_id=document_id,
                chunk_id=chunk.chunk_id,
                text_snippet=chunk.text[:150] + "...", # Just a snippet for the UI
                heading=chunk.heading,
                page_number=chunk.metadata.get("page_num", 1)
            ))
            
        if debug:
            trace["reranking_results"] = [
                {
                    "chunk_id": c.chunk_id,
                    "original_distance": c.original_distance,
                    "semantic_similarity": c.semantic_similarity,
                    "ocr_confidence": c.ocr_confidence,
                    "final_score": c.final_score,
                    "status": c.status,
                    "heading": c.heading,
                    "text_snippet": c.text[:100] + "..."
                } for c in all_scored_chunks
            ]
            
        full_context = "\n".join(context_blocks)
        return full_context, citations, trace
