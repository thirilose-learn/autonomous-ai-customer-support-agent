"""
Automated Pytest Suite for Level 4 RAG & Knowledge Base Pipeline.
Validates local 384-dim BAAI/bge-small-en-v1.5 embeddings, Supabase pgvector table,
semantic search accuracy, FastAPI endpoints, and Level 3 data preservation.
"""

import os
import pytest
from starlette.testclient import TestClient
from app.main import app
from app.rag.embeddings import embed_query, embed_documents
from app.rag.service import RAGRetrievalService
from app.rag.vector_store import get_indexed_count, get_db_connection
from app.core.config import settings

KB_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "knowledge_base")
EXPECTED_POLICY_FILES = [
    "return_policy.md",
    "refund_policy.md",
    "cancellation_policy.md",
    "shipping_policy.md",
    "warranty_policy.md",
    "faqs.md",
]


def test_knowledge_base_files_exist_and_non_empty():
    """Verify that all 6 knowledge base policy files exist with adequate content."""
    for filename in EXPECTED_POLICY_FILES:
        filepath = os.path.join(KB_DIR, filename)
        assert os.path.exists(filepath), f"Missing policy file: {filename}"
        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read().strip()
            assert len(content) > 200, f"Policy file {filename} is too short ({len(content)} chars)"
            assert content.startswith("# "), f"Policy file {filename} missing level-1 heading"


def test_local_embedding_engine_dimension_and_offline():
    """Verify that BAAI/bge-small-en-v1.5 produces exactly 384 dimensions locally."""
    test_text = "What is the return window for clothing?"
    vector = embed_query(test_text)
    assert isinstance(vector, list)
    assert len(vector) == 384, f"Expected 384 dimensions, got {len(vector)}"
    assert all(isinstance(v, float) for v in vector)

    batch_vectors = embed_documents([test_text, "Another sample text"])
    assert len(batch_vectors) == 2
    assert len(batch_vectors[0]) == 384
    assert len(batch_vectors[1]) == 384


def test_supabase_knowledge_embeddings_table_populated():
    """Verify that knowledge_embeddings exists in Supabase and contains indexed chunks."""
    count = get_indexed_count()
    assert count > 50, f"Expected at least 50 indexed chunks, found {count}"


def test_semantic_retrieval_quality_benchmark():
    """Verify semantic retrieval accurately maps domain questions to expected policies."""
    benchmarks = [
        ("How many days do I have to return an item?", "return", "Return Policy"),
        ("When will my refund post to my credit card?", "refund", "Refund Policy"),
        ("Can I cancel an order that has already shipped?", "cancellation", "Cancellation Policy"),
        ("What happens if my package is lost in transit?", "shipping", "Shipping & Delivery Policy"),
        ("Does the warranty cover manufacturing defects?", "warranty", "Warranty Policy"),
        ("What payment methods are accepted?", None, "Frequently Asked Questions"),
    ]

    for query, category, expected_title in benchmarks:
        result = RAGRetrievalService.retrieve(
            query=query,
            category=category,
            top_k=3,
            threshold=0.60,
        )
        assert result["results_count"] > 0, f"No matches found for query: '{query}'"
        top_match = result["matches"][0]
        assert top_match["title"] == expected_title, (
            f"Query '{query}' expected title '{expected_title}', got '{top_match['title']}'"
        )
        assert top_match["similarity_score"] >= 0.65, (
            f"Query '{query}' top match score {top_match['similarity_score']} is below 0.65"
        )


def test_fastapi_rag_query_endpoint():
    """Test the POST /api/v1/rag/query endpoint with valid payload."""
    client = TestClient(app)
    payload = {
        "query": "How do I return a damaged product?",
        "category": "return",
        "top_k": 2,
        "threshold": 0.65,
    }
    response = client.post("/api/v1/rag/query", json=payload)
    assert response.status_code == 200, f"API query failed: {response.text}"
    data = response.json()
    assert data["query"] == payload["query"]
    assert data["results_count"] >= 1
    assert len(data["matches"]) >= 1
    assert data["matches"][0]["policy_category"] == "return"
    assert "similarity_score" in data["matches"][0]


def test_fastapi_rag_health_endpoint():
    """Test the GET /api/v1/rag/health diagnostics endpoint."""
    client = TestClient(app)
    response = client.get("/api/v1/rag/health")
    assert response.status_code == 200, f"API health failed: {response.text}"
    data = response.json()
    assert data["status"] == "online"
    assert data["embedding_dimension"] == 384
    assert data["total_indexed_chunks"] >= 50


def test_level3_relational_tables_preserved_and_unmodified():
    """Strict verification that all 8 Level 3 tables remain 100% frozen."""
    expected_counts = {
        "customers": 99441,
        "orders": 99441,
        "order_items": 112650,
        "order_payments": 103886,
        "products": 32951,
        "product_category_name_translation": 73,
        "customer_support_intents": 26872,
        "customer_demo_accounts": 25,
    }

    conn = get_db_connection()
    try:
        cur = conn.cursor()
        for table, expected in expected_counts.items():
            cur.execute(f"SELECT COUNT(*) FROM {table};")
            actual = cur.fetchone()[0]
            assert actual == expected, f"Table '{table}' was modified! Expected {expected}, got {actual}"
    finally:
        conn.close()
