"""
DocuMind AI — Confidence-Aware Reranking
==========================================
WHY RERANKING?
    Vector similarity (Cosine Distance) only measures semantic overlap. 
    It doesn't know if a chunk is garbage OCR noise or a high-quality paragraph.
    
    This reranker takes a larger pool of vector results (e.g. Top 15) and
    re-scores them using a weighted formula that considers:
    1. Semantic Similarity (from ChromaDB)
    2. OCR Confidence (from our metadata)
    3. Structural Relevance (Headings)
"""

from typing import List, Dict, Any
from pydantic import BaseModel
from loguru import logger

class ScoredChunk(BaseModel):
    chunk_id: str
    text: str
    metadata: Dict[str, Any]
    original_distance: float
    semantic_similarity: float
    ocr_confidence: float
    final_score: float
    status: str = "accepted" # "accepted", "penalized", "discarded"
    heading: str

class ConfidenceReranker:
    
    # Weights for the scoring formula
    WEIGHT_SEMANTIC = 0.7
    WEIGHT_OCR = 0.3
    HEADING_BOOST = 0.05
    
    # Thresholds
    DISCARD_THRESHOLD = 0.4  # Chunks below this confidence are entirely discarded
    PENALTY_THRESHOLD = 0.7  # Chunks below this confidence receive a semantic penalty

    @classmethod
    def rerank(cls, ids: List[str], texts: List[str], metadatas: List[Dict[str, Any]], distances: List[float], top_k: int) -> tuple[List[ScoredChunk], List[ScoredChunk]]:
        """
        Takes raw results from ChromaDB, scores them, filters them, and returns the top_k.
        Returns: (top_k_chunks, all_scored_chunks_for_trace)
        """
        scored_chunks: List[ScoredChunk] = []
        
        for i in range(len(ids)):
            chunk_id = ids[i]
            text = texts[i]
            meta = metadatas[i]
            # ChromaDB cosine distance: 0 is identical, 1 is orthogonal. 
            # Similarity = 1 - distance
            distance = distances[i] if distances[i] is not None else 0.0
            similarity = 1.0 - distance
            
            heading = meta.get("heading", "Unknown Section")
            ocr_conf = meta.get("avg_confidence", 1.0)
            
            status = "accepted"
            
            # 1. Hard Filter (Garbage OCR)
            if ocr_conf < cls.DISCARD_THRESHOLD:
                status = "discarded"
                final_score = 0.0
            else:
                # 2. Base Scoring
                score = (similarity * cls.WEIGHT_SEMANTIC) + (ocr_conf * cls.WEIGHT_OCR)
                
                # 3. Structural Boost
                if heading and heading != "Unknown Section":
                    score += cls.HEADING_BOOST
                    
                # 4. Semantic Penalty for low confidence
                if ocr_conf < cls.PENALTY_THRESHOLD:
                    status = "penalized"
                    score *= 0.85 # 15% penalty to the final score
                    
                final_score = score
                
            scored_chunks.append(ScoredChunk(
                chunk_id=chunk_id,
                text=text,
                metadata=meta,
                original_distance=distance,
                semantic_similarity=similarity,
                ocr_confidence=ocr_conf,
                final_score=final_score,
                status=status,
                heading=heading
            ))
            
        # Sort by final score descending
        scored_chunks.sort(key=lambda x: x.final_score, reverse=True)
        
        # Filter out discarded
        valid_chunks = [c for c in scored_chunks if c.status != "discarded"]
        
        # Take Top K
        top_chunks = valid_chunks[:top_k]
        
        logger.info(f"Reranker: Processed {len(ids)} chunks. Discarded {len(scored_chunks) - len(valid_chunks)}. Returning Top {len(top_chunks)}.")
        
        return top_chunks, scored_chunks
