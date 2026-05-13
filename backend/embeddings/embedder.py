"""
DocuMind AI — Unified Embedding Engine (Ollama)
================================================
WHY OLLAMA FOR EMBEDDINGS?
    1. System Stability: Resolves PyTorch DLL initialization errors on Windows.
    2. Consistency: Uses the same local engine as the Chat LLM.
    3. Resource Management: One engine (Ollama) manages both LLM and Embedding models.
"""

import httpx
from typing import List
from loguru import logger

from backend.config.settings import settings
from backend.embeddings.chunker import DocumentChunk

class EmbeddingEngine:
    """Uses Ollama's API to generate embeddings for text chunks."""
    
    def __init__(self):
        self.base_url = settings.ollama_base_url
        self.model = settings.embedding_model # e.g., "mxbai-embed-large" or "llama3"
        self.timeout = httpx.Timeout(60.0)
        logger.info(f"Initialized Ollama Embedding Engine using model: {self.model}")

    async def _get_embedding(self, text: str) -> List[float]:
        """Calls Ollama's /api/embeddings endpoint for a single text."""
        url = f"{self.base_url}/api/embeddings"
        payload = {
            "model": self.model,
            "prompt": text,
            "options": {
                "num_gpu": settings.ollama_num_gpu
            }
        }
        
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(url, json=payload)
            response.raise_for_status()
            return response.json()["embedding"]

    def embed_chunks(self, chunks: List[DocumentChunk]) -> List[List[float]]:
        """
        Generates embeddings for a list of chunks.
        Note: This is currently synchronous for compatibility with the service layer,
        but it calls a helper that handles the HTTP request.
        """
        import asyncio
        
        embeddings = []
        logger.info(f"Generating embeddings for {len(chunks)} chunks via Ollama...")
        
        # In a real production system, we'd use asyncio.gather for parallelism
        for i, chunk in enumerate(chunks):
            if i % 10 == 0 and i > 0:
                logger.debug(f"Embedded {i}/{len(chunks)} chunks...")
            
            # Since this tool is used in a sync-called thread pool usually, 
            # we can run the async helper in a new event loop or use a sync client.
            # For simplicity and reliability, we'll use a sync httpx client here.
            try:
                with httpx.Client(timeout=self.timeout) as client:
                    url = f"{self.base_url}/api/embeddings"
                    payload = {
                        "model": self.model,
                        "prompt": chunk.text,
                        "options": {"num_gpu": settings.ollama_num_gpu}
                    }
                    response = client.post(url, json=payload)
                    response.raise_for_status()
                    embeddings.append(response.json()["embedding"])
            except Exception as e:
                logger.error(f"Embedding failed for chunk {i}: {e}")
                raise RuntimeError(f"Ollama embedding failed: {e}")
                
        return embeddings

    def embed_query(self, query: str) -> List[float]:
        """Generates an embedding for a single query string."""
        logger.debug(f"Generating query embedding: '{query[:50]}...'")
        with httpx.Client(timeout=self.timeout) as client:
            url = f"{self.base_url}/api/embeddings"
            payload = {
                "model": self.model,
                "prompt": query,
                "options": {"num_gpu": settings.ollama_num_gpu}
            }
            response = client.post(url, json=payload)
            response.raise_for_status()
            return response.json()["embedding"]

# Singleton
embedding_engine = None

def get_embedding_engine() -> EmbeddingEngine:
    global embedding_engine
    if embedding_engine is None:
        embedding_engine = EmbeddingEngine()
    return embedding_engine
