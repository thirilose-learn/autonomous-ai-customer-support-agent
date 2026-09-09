"""
Free Local Embedding Engine using FastEmbed (BAAI/bge-small-en-v1.5).
Executes 100% offline via local ONNX runtime with zero external API calls.
Strictly produces 384-dimensional vectors.
"""

from typing import List, Optional
from fastembed import TextEmbedding
from app.core.config import settings

_embedding_model_instance: Optional[TextEmbedding] = None


def get_embedding_model() -> TextEmbedding:
    """
    Initializes or returns the cached local FastEmbed model singleton.
    Uses BAAI/bge-small-en-v1.5 on CPU.
    """
    global _embedding_model_instance
    if _embedding_model_instance is None:
        _embedding_model_instance = TextEmbedding(
            model_name=settings.EMBEDDING_MODEL
        )
    return _embedding_model_instance


def embed_query(query: str) -> List[float]:
    """
    Generates a 384-dimensional embedding for a single query string.
    """
    model = get_embedding_model()
    embeddings = list(model.embed([query]))
    vector = embeddings[0].tolist()
    
    # Strictly verify vector dimension
    if len(vector) != settings.EMBEDDING_DIM:
        raise ValueError(
            f"Embedding dimension mismatch: expected {settings.EMBEDDING_DIM}, got {len(vector)}"
        )
    return vector


def embed_documents(documents: List[str], batch_size: int = 64) -> List[List[float]]:
    """
    Generates 384-dimensional embeddings for a batch of document texts.
    """
    if not documents:
        return []
    model = get_embedding_model()
    embeddings = list(model.embed(documents, batch_size=batch_size))
    result = [e.tolist() for e in embeddings]
    
    # Strictly verify vector dimensions
    for idx, vec in enumerate(result):
        if len(vec) != settings.EMBEDDING_DIM:
            raise ValueError(
                f"Embedding dimension mismatch at index {idx}: expected {settings.EMBEDDING_DIM}, got {len(vec)}"
            )
    return result
