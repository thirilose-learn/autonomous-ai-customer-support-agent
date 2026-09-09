"""
Knowledge Base Indexer.
Loads policy markdown files, parses nodes with LlamaIndex SentenceSplitter,
generates 384-dim embeddings locally via FastEmbed (BAAI/bge-small-en-v1.5),
and stores them in Supabase PostgreSQL (pgvector).
"""

import os
import sys
import time
from dotenv import load_dotenv

# Ensure backend app is in Python path
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(BASE_DIR, "backend"))

load_dotenv(os.path.join(BASE_DIR, "backend", ".env"))

from app.rag.ingestion import load_and_chunk_knowledge_base
from app.rag.embeddings import embed_documents
from app.rag.vector_store import clear_knowledge_embeddings, insert_chunks, get_indexed_count


def run_indexing():
    kb_dir = os.path.join(BASE_DIR, "knowledge_base")
    print("==================================================")
    print("STARTING KNOWLEDGE BASE INDEXING (FREE LOCAL RAG)")
    print(f"Knowledge Base Directory: {kb_dir}")
    print("Embedding Model: BAAI/bge-small-en-v1.5 (384 dims, Local CPU)")
    print("==================================================")

    # 1. Parse & Chunk
    t0 = time.time()
    print("\n--> 1. Loading and chunking markdown policy documents...")
    chunks = load_and_chunk_knowledge_base(kb_dir)
    print(f"    Generated {len(chunks)} semantic chunks from policy files.")

    # Breakdown by category
    categories = {}
    for c in chunks:
        cat = c["policy_category"]
        categories[cat] = categories.get(cat, 0) + 1
    print("    Category Breakdown:")
    for cat, count in sorted(categories.items()):
        print(f"      - {cat}: {count} chunks")

    # 2. Local Embedding Generation
    print("\n--> 2. Generating local embeddings via FastEmbed (ONNX CPU)...")
    texts = [c["content"] for c in chunks]
    t_embed_start = time.time()
    embeddings = embed_documents(texts, batch_size=32)
    t_embed_elapsed = time.time() - t_embed_start
    print(f"    Generated {len(embeddings)} embeddings in {t_embed_elapsed:.2f}s ({len(embeddings)/max(t_embed_elapsed, 0.01):.1f} chunks/s).")

    # Attach vectors to chunks
    for idx, chunk in enumerate(chunks):
        chunk["embedding"] = embeddings[idx]

    # 3. Store in Supabase pgvector
    print("\n--> 3. Storing chunks and vectors into Supabase PostgreSQL...")
    clear_knowledge_embeddings()
    inserted = insert_chunks(chunks)
    print(f"    Inserted {inserted} records into 'knowledge_embeddings' table.")

    # 4. Verify Total Count
    total_in_db = get_indexed_count()
    print(f"\n--> 4. Verification: Total indexed records in database = {total_in_db}")

    total_time = time.time() - t0
    print("\n==================================================")
    print(f"INDEXING COMPLETE: {total_in_db} chunks indexed in {total_time:.2f}s")
    print("==================================================")


if __name__ == "__main__":
    run_indexing()
