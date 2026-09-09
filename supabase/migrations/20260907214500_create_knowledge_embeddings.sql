-- ==============================================================================
-- Level 4 Migration: Knowledge Base Vector Embeddings Table
-- Model: BAAI/bge-small-en-v1.5 (384-dimensional free open-source embeddings)
-- All existing Level 3 tables remain 100% frozen and untouched.
-- ==============================================================================

-- 1. Create Knowledge Embeddings Table (vector dimension = 384)
CREATE TABLE IF NOT EXISTS knowledge_embeddings (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    doc_id VARCHAR(100) NOT NULL,
    policy_category VARCHAR(100) NOT NULL,
    title VARCHAR(200) NOT NULL,
    section VARCHAR(200),
    content TEXT NOT NULL,
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    embedding vector(384),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 2. HNSW Vector Index for Cosine Similarity Search
CREATE INDEX IF NOT EXISTS idx_knowledge_embeddings_vector 
ON knowledge_embeddings 
USING hnsw (embedding vector_cosine_ops)
WITH (m = 16, ef_construction = 64);

-- 3. Filter Index on Policy Category
CREATE INDEX IF NOT EXISTS idx_knowledge_embeddings_category 
ON knowledge_embeddings(policy_category);
