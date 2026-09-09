"""
Vector Store repository for Supabase PostgreSQL (pgvector).
Manages chunk insertion, HNSW similarity search, and category filtering.
"""

import json
from typing import List, Dict, Any, Optional
import psycopg2
from psycopg2.extras import RealDictCursor
from app.core.config import settings


def get_db_connection():
    if not settings.DATABASE_URL:
        raise ValueError("DATABASE_URL is not configured in settings/environment.")
    return psycopg2.connect(settings.DATABASE_URL, connect_timeout=15)


def insert_chunks(chunks: List[Dict[str, Any]]) -> int:
    """
    Inserts a list of document chunks and their 384-dim embeddings into knowledge_embeddings.
    Each chunk dict must contain:
    doc_id, policy_category, title, section, content, metadata, embedding (list of 384 floats).
    """
    if not chunks:
        return 0

    sql = """
    INSERT INTO knowledge_embeddings (
        doc_id, policy_category, title, section, content, metadata, embedding
    ) VALUES (
        %s, %s, %s, %s, %s, %s, %s::vector
    );
    """

    conn = get_db_connection()
    try:
        cur = conn.cursor()
        for chunk in chunks:
            cur.execute(
                sql,
                (
                    chunk["doc_id"],
                    chunk["policy_category"],
                    chunk["title"],
                    chunk.get("section"),
                    chunk["content"],
                    json.dumps(chunk.get("metadata", {})),
                    chunk["embedding"],
                ),
            )
        conn.commit()
        return len(chunks)
    finally:
        conn.close()


def search_chunks(
    query_vector: List[float],
    top_k: int = 3,
    category: Optional[str] = None,
    threshold: Optional[float] = None,
) -> List[Dict[str, Any]]:
    """
    Executes cosine similarity search against knowledge_embeddings using HNSW index.
    Cosine similarity = 1 - (embedding <=> query_vector).
    """
    if threshold is None:
        threshold = settings.RAG_SIMILARITY_THRESHOLD

    conditions = []
    params: List[Any] = [query_vector]

    if category:
        conditions.append("policy_category = %s")
        params.append(category)

    # Filter out chunks below similarity threshold
    conditions.append("(1 - (embedding <=> %s::vector)) >= %s")
    params.extend([query_vector, threshold])

    where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""
    
    # Query ordering params
    params.extend([query_vector, top_k])

    sql = f"""
    SELECT 
        id::text,
        doc_id,
        policy_category,
        title,
        section,
        content,
        metadata,
        (1 - (embedding <=> %s::vector)) AS similarity_score
    FROM knowledge_embeddings
    {where_clause}
    ORDER BY embedding <=> %s::vector ASC
    LIMIT %s;
    """

    conn = get_db_connection()
    try:
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute(sql, tuple(params))
        results = [dict(row) for row in cur.fetchall()]
        return results
    finally:
        conn.close()


def get_indexed_count() -> int:
    """Returns the total number of knowledge chunks indexed in Supabase."""
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM knowledge_embeddings;")
        return cur.fetchone()[0]
    finally:
        conn.close()


def clear_knowledge_embeddings() -> int:
    """Clears knowledge_embeddings table prior to re-indexing (keeps Level 3 tables intact)."""
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        cur.execute("DELETE FROM knowledge_embeddings;")
        deleted = cur.rowcount
        conn.commit()
        return deleted
    finally:
        conn.close()
