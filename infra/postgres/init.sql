CREATE EXTENSION IF NOT EXISTS vector;

-- The application migration layer owns tables. Keeping this extension explicit
-- makes semantic retrieval available when Vertex embeddings are enabled.
