"""
RAG Semantic Search Endpoints.
Provides knowledge base retrieval for policy and FAQ inquiries.
"""

from fastapi import APIRouter, HTTPException, status
from app.schemas.rag import RAGQueryRequest, RAGQueryResponse, RAGHealthResponse
from app.rag.service import RAGRetrievalService

router = APIRouter()


@router.post(
    "/query",
    response_model=RAGQueryResponse,
    status_code=status.HTTP_200_OK,
    summary="Semantic Policy & FAQ Query",
    description="Embeds a customer query using local BAAI/bge-small-en-v1.5 and returns top matching policy clauses.",
)
def query_knowledge_base(payload: RAGQueryRequest) -> RAGQueryResponse:
    try:
        results = RAGRetrievalService.retrieve(
            query=payload.query,
            category=payload.category,
            top_k=payload.top_k,
            threshold=payload.threshold,
        )
        return RAGQueryResponse(**results)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Semantic retrieval failed: {str(exc)}",
        )


@router.get(
    "/health",
    response_model=RAGHealthResponse,
    status_code=status.HTTP_200_OK,
    summary="RAG Subsystem Health Diagnostics",
    description="Returns vector storage status, model configuration, and indexed chunk count.",
)
def get_rag_health() -> RAGHealthResponse:
    try:
        diagnostics = RAGRetrievalService.get_health()
        return RAGHealthResponse(**diagnostics)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"RAG health check failed: {str(exc)}",
        )
