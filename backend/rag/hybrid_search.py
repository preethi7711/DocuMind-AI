"""
DocuMind AI — Hybrid Search (RRF)
==================================
WHY HYBRID SEARCH?
    Dense vectors (SentenceTransformers) are amazing at semantic matching
    ("money" -> "banking"), but terrible at exact keyword matching ("Booth").
    Sparse vectors (BM25) are amazing at keywords, but terrible at semantics.
    
    We combine both using Reciprocal Rank Fusion (RRF).
"""

from typing import List, Dict, Any, Tuple
from loguru import logger
from rank_bm25 import BM25Okapi

class HybridSearch:
    @staticmethod
    def _tokenize(text: str) -> List[str]:
        # Simple whitespace tokenization, lowercase, strip punctuation
        import string
        return text.lower().translate(str.maketrans('', '', string.punctuation)).split()

    @staticmethod
    def compute_rrf(vector_results: Dict[str, Any], bm25_results: List[Tuple[str, float, str, Dict[str, Any]]], top_k: int = 15) -> Tuple[List[str], List[str], List[Dict[str, Any]], List[float]]:
        """
        Combines vector results and BM25 results using Reciprocal Rank Fusion.
        """
        k = 60 # RRF constant
        
        # 1. Rank Vector Results
        vector_ids = vector_results.get('ids', [[]])[0]
        vector_docs = vector_results.get('documents', [[]])[0]
        vector_metas = vector_results.get('metadatas', [[]])[0]
        vector_distances = vector_results.get('distances', [[]])[0] if 'distances' in vector_results and vector_results['distances'] else [0.0] * len(vector_ids)
        
        # Build lookup
        chunk_lookup = {}
        for i, cid in enumerate(vector_ids):
            chunk_lookup[cid] = {
                "text": vector_docs[i],
                "metadata": vector_metas[i],
                "vector_distance": vector_distances[i],
                "vector_rank": i + 1,
                "bm25_rank": 0
            }
            
        # 2. Rank BM25 Results
        for i, (cid, score, text, meta) in enumerate(bm25_results):
            if cid not in chunk_lookup:
                chunk_lookup[cid] = {
                    "text": text,
                    "metadata": meta,
                    "vector_distance": 1.0, # Default high distance
                    "vector_rank": 0,
                    "bm25_rank": i + 1
                }
            else:
                chunk_lookup[cid]["bm25_rank"] = i + 1

        # 3. Calculate RRF Score
        fused_scores = []
        for cid, data in chunk_lookup.items():
            vr = data["vector_rank"]
            br = data["bm25_rank"]
            
            vr_score = 1.0 / (k + vr) if vr > 0 else 0.0
            br_score = 1.0 / (k + br) if br > 0 else 0.0
            rrf_score = vr_score + br_score
            
            fused_scores.append((rrf_score, cid, data))
            
        # 4. Sort by RRF Score descending
        fused_scores.sort(key=lambda x: x[0], reverse=True)
        
        # 5. Extract Top K
        top_candidates = fused_scores[:top_k]
        
        out_ids = []
        out_texts = []
        out_metas = []
        out_distances = [] # We'll pass the original vector distance to the reranker
        
        for rrf_score, cid, data in top_candidates:
            out_ids.append(cid)
            out_texts.append(data["text"])
            out_metas.append(data["metadata"])
            out_distances.append(data["vector_distance"])
            
        logger.info(f"Hybrid Search: Fused {len(vector_ids)} vector and {len(bm25_results)} BM25 results into Top {len(out_ids)}.")
        return out_ids, out_texts, out_metas, out_distances

    @classmethod
    def search(cls, query: str, document_id: str, vector_store, query_embedding: List[float], initial_k: int) -> Tuple[List[str], List[str], List[Dict[str, Any]], List[float]]:
        # 1. Vector Search
        vector_results = vector_store.collection.query(
            query_embeddings=[query_embedding],
            n_results=initial_k,
            where={"document_id": document_id}
        )
        
        # 2. BM25 Search
        # Fetch all chunks for this document. For massive documents this should be cached 
        # or pushed to SQLite FTS, but for MVP, ChromaDB `.get` is very fast.
        doc_chunks = vector_store.collection.get(
            where={"document_id": document_id},
            include=["documents", "metadatas"]
        )
        
        ids = doc_chunks.get('ids', [])
        docs = doc_chunks.get('documents', [])
        metas = doc_chunks.get('metadatas', [])
        
        if not ids:
            return [], [], [], []
            
        tokenized_corpus = [cls._tokenize(doc) for doc in docs]
        bm25 = BM25Okapi(tokenized_corpus)
        
        tokenized_query = cls._tokenize(query)
        bm25_scores = bm25.get_scores(tokenized_query)
        
        # Pair up scores and sort
        scored_docs = list(zip(ids, bm25_scores, docs, metas))
        scored_docs.sort(key=lambda x: x[1], reverse=True)
        
        # Take Top K from BM25
        top_bm25 = scored_docs[:initial_k]
        
        # 3. Fuse!
        return cls.compute_rrf(vector_results, top_bm25, top_k=initial_k)
