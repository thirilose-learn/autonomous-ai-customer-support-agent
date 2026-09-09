from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


class RAGQueryRequest(BaseModel):
    query: str = Field(..., min_length=2, description="Customer question or search term")
    category: Optional[str] = Field(
        None,
        description="Optional policy category filter (e.g., return, refund, cancellation, shipping, warranty, faqs)",
    )
    top_k: int = Field(default=3, ge=1, le=10, description="Maximum number of relevant chunks to retrieve")
    threshold: Optional[float] = Field(
        default=None,
        ge=0.0,
        le=1.0,
        description="Optional minimum cosine similarity cutoff (defaults to server configuration)",
    )


class RAGMatch(BaseModel):
    id: str
    doc_id: str
    policy_category: str
    title: str
    section: Optional[str] = None
    content: str
    similarity_score: float
    metadata: Dict[str, Any] = Field(default_factory=dict)


class RAGQueryResponse(BaseModel):
    query: str
    category_filter: Optional[str] = None
    results_count: int
    threshold_applied: float
    matches: List[RAGMatch]


class RAGHealthResponse(BaseModel):
    status: str
    embedding_model: str
    embedding_dimension: int
    vector_database: str
    total_indexed_chunks: int
