"""
DocuMind AI — Intelligent Text Chunking
=========================================
WHY WE DO THIS:
    LLMs have context windows. We can't feed a 500-page PDF into an LLM.
    We must break the document into "chunks" and search them.
    
    NAIVE CHUNKING: Split text every 500 characters. 
    Problem: It cuts sentences in half ("The company revenue was $" | "5 million").
    
    INTELLIGENT CHUNKING: We use our LayoutAnalyzer's `TextBlock` objects.
    We chunk by Paragraphs. We never break a paragraph unless it exceeds the chunk limit.
    Even better, we track the LAST SEEN HEADING and inject it into the chunk's metadata!
    This gives the Embedding model massive context.
"""

from typing import List, Dict, Any
from pydantic import BaseModel
from loguru import logger

from backend.config.settings import settings
from backend.api.schemas.extraction import StructuredDocument, TextBlock

class DocumentChunk(BaseModel):
    """Represents a single chunk of text ready to be embedded."""
    chunk_id: str
    document_id: str
    text: str
    metadata: Dict[str, Any]

class ChunkingEngine:
    """Intelligently chunks structured documents."""

    @staticmethod
    def chunk_document(document: StructuredDocument, max_chars: int = settings.rag_chunk_size, overlap: int = settings.rag_chunk_overlap) -> List[DocumentChunk]:
        """
        Groups TextBlocks into semantic chunks.
        Tracks the active heading to enrich chunk metadata.
        """
        logger.info(f"Chunking document {document.document_id}")
        chunks: List[DocumentChunk] = []
        
        current_chunk_text = ""
        current_chunk_blocks: List[TextBlock] = []
        current_heading = "Unknown Section"
        chunk_index = 0
        
        # Helper to finalize and store a chunk
        def save_chunk(text: str, heading: str, blocks: List[TextBlock]):
            nonlocal chunk_index
            if not text.strip():
                return
            
            # Calculate average OCR confidence for the chunk
            avg_confidence = 1.0
            if blocks:
                confs = []
                for b in blocks:
                    for line in b.lines:
                        confs.append(line.confidence)
                if confs:
                    avg_confidence = sum(confs) / len(confs)
            
            # We inject the heading directly into the text so the embedding model
            # captures the semantic relationship between the section title and the content.
            enriched_text = f"[{heading}]\n{text.strip()}"
            
            chunk = DocumentChunk(
                chunk_id=f"{document.document_id}_chunk_{chunk_index}",
                document_id=document.document_id,
                text=enriched_text,
                metadata={
                    "document_id": document.document_id,
                    "heading": heading,
                    "chunk_index": chunk_index,
                    "avg_confidence": round(avg_confidence, 4)
                }
            )
            chunks.append(chunk)
            chunk_index += 1

        for page in document.pages:
            for block in page.blocks:
                # If we hit a new heading, we finalize the current chunk immediately.
                # Why? We don't want a single chunk containing data from two unrelated sections.
                if block.type == "heading":
                    save_chunk(current_chunk_text, current_heading, current_chunk_blocks)
                    current_chunk_text = ""
                    current_chunk_blocks = []
                    current_heading = block.text
                    continue
                
                # If it's a paragraph, see if adding it exceeds our character limit
                block_len = len(block.text)
                if len(current_chunk_text) + block_len > max_chars and current_chunk_text:
                    save_chunk(current_chunk_text, current_heading, current_chunk_blocks)
                    # Start new chunk with overlap (we take the last `overlap` characters from the old chunk)
                    # Note: In a production tokenizer, we'd do overlap by Tokens, not Characters.
                    overlap_text = current_chunk_text[-overlap:] if overlap > 0 else ""
                    current_chunk_text = overlap_text + "\n" + block.text
                    current_chunk_blocks = [block] # We lose overlap block context here for MVP, but good enough
                else:
                    current_chunk_text += "\n" + block.text
                    current_chunk_blocks.append(block)

        # Save any remaining text
        if current_chunk_text:
            save_chunk(current_chunk_text, current_heading, current_chunk_blocks)
            
        logger.info(f"Created {len(chunks)} chunks for document {document.document_id}")
        return chunks
