"""
High-level RAG Retrieval Service for policy and FAQ knowledge lookup.
Coordinates local FastEmbed inference and Supabase pgvector nearest neighbor search.
"""

from typing import Dict, Any, Optional, List
from app.core.config import settings
from app.rag.embeddings import embed_query
from app.rag.vector_store import search_chunks, get_indexed_count


class RAGRetrievalService:
    @staticmethod
    def retrieve(
        query: str,
        category: Optional[str] = None,
        top_k: Optional[int] = None,
        threshold: Optional[float] = None,
    ) -> Dict[str, Any]:
        """
        Executes end-to-end semantic retrieval for a customer query:
        1. Generates 384-dimensional query vector locally on CPU.
        2. Queries Supabase knowledge_embeddings via HNSW index.
        3. Applies optional category filter and minimum similarity threshold.
        """
        if top_k is None:
            top_k = settings.RAG_TOP_K
        if threshold is None:
            threshold = settings.RAG_SIMILARITY_THRESHOLD

        # 1. Local free open-source embedding
        query_vector = embed_query(query)

        # 2. Vector search in PostgreSQL
        raw_matches = search_chunks(
            query_vector=query_vector,
            top_k=top_k,
            category=category,
            threshold=threshold,
        )

        matches = []
        for m in raw_matches:
            matches.append({
                "id": str(m["id"]),
                "doc_id": m["doc_id"],
                "policy_category": m["policy_category"],
                "title": m["title"],
                "section": m.get("section"),
                "content": m["content"],
                "similarity_score": round(float(m["similarity_score"]), 4),
                "metadata": m.get("metadata") or {},
            })

        return {
            "query": query,
            "category_filter": category,
            "results_count": len(matches),
            "threshold_applied": threshold,
            "matches": matches,
        }

    @staticmethod
    def get_health() -> Dict[str, Any]:
        """Returns health diagnostics for the RAG subsystem."""
        total_chunks = get_indexed_count()
        return {
            "status": "online",
            "embedding_model": settings.EMBEDDING_MODEL,
            "embedding_dimension": settings.EMBEDDING_DIM,
            "vector_database": "Supabase pgvector (HNSW cosine)",
            "total_indexed_chunks": total_chunks,
        }
