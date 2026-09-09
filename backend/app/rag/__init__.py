"""
RAG Package for Policy & FAQ Knowledge Retrieval.
"""

from app.rag.embeddings import get_embedding_model, embed_query, embed_documents
from app.rag.service import RAGRetrievalService
from app.rag.vector_store import search_chunks, get_indexed_count

__all__ = [
    "get_embedding_model",
    "embed_query",
    "embed_documents",
    "RAGRetrievalService",
    "search_chunks",
    "get_indexed_count",
]
