-- ============================================================
-- 数据库初始化脚本 — AI Trip Agent
-- 由 Docker Compose 在 PostgreSQL 首次启动时自动执行
-- ============================================================

-- 启用 pgvector 扩展
CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS pgcrypto;

-- 旅游知识切片表
CREATE TABLE IF NOT EXISTS knowledge_chunks (
    id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    city          VARCHAR(50)  NOT NULL,
    category      VARCHAR(20)  NOT NULL,
    title         VARCHAR(200) NOT NULL,
    content       TEXT         NOT NULL,
    embedding     VECTOR(1024) NOT NULL,
    metadata      JSONB        DEFAULT '{}',
    created_at    TIMESTAMPTZ  DEFAULT NOW()
);

-- 向量索引（IVFFlat，适合中小规模数据）
CREATE INDEX IF NOT EXISTS idx_chunks_embedding
    ON knowledge_chunks USING ivfflat (embedding vector_cosine_ops)
    WITH (lists = 20);

-- 城市 + 类别联合索引（过滤加速）
CREATE INDEX IF NOT EXISTS idx_chunks_city_category
    ON knowledge_chunks (city, category);

-- 全文搜索索引（可选，用于混合检索）
CREATE INDEX IF NOT EXISTS idx_chunks_content_gin
    ON knowledge_chunks USING gin (to_tsvector('simple', content));
