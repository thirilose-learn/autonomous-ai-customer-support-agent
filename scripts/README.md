# Utility Scripts

This directory contains standalone data engineering, database setup, and knowledge-base indexing utilities for the project:

- **`apply_migrations.py`**: Executes all SQL schema migrations from `supabase/migrations/` sequentially into the PostgreSQL database.
- **`prepare_data.py`**: Preprocesses raw e-commerce CSV datasets, handles schema normalization, and translates Portuguese categories to English (using `translations.py`).
- **`translations.py`**: Translation dictionary mapping Portuguese product categories to English.
- **`select_demo_customers.py`**: Samples and exports representative customer profiles with varied order histories for testing and demonstration.
- **`fast_reliable_ingest.py`**: Robust bulk data ingestion script to load cleaned relational datasets directly into PostgreSQL/Supabase.
- **`index_knowledge_base.py`**: Parses markdown documents from `knowledge_base/`, generates dense vector embeddings via BAAI/bge-small-en-v1.5, and populates the `knowledge_embeddings` vector table.
