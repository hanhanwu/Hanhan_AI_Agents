-- supabase/migrations/002_vector_catalog.sql
--
-- Product catalog stored as pgvector embeddings.
-- LangChain's SupabaseVectorStore expects:
--   - table with `id`, `content`, `metadata`, `embedding` columns
--   - a match function named after `query_name` in get_vector_store()

-- Enable the pgvector extension (already enabled on Supabase by default)
create extension if not exists vector;

create table if not exists product_catalog (
    id        bigserial primary key,
    content   text         not null,   -- the chunk text LangChain will return
    metadata  jsonb        not null default '{}',
    embedding vector(1536) not null    -- matches text-embedding-3-small dimensions
);

-- IVFFlat index for approximate nearest-neighbour search
-- lists=100 is a reasonable default for up to ~1M rows
create index if not exists product_catalog_embedding_idx
    on product_catalog
    using ivfflat (embedding vector_cosine_ops)
    with (lists = 100);

-- Match function required by LangChain SupabaseVectorStore
create or replace function match_products(
    query_embedding vector(1536),
    match_count     int     default 5,
    filter          jsonb   default '{}'
)
returns table (
    id        bigint,
    content   text,
    metadata  jsonb,
    similarity float
)
language plpgsql
as $$
begin
    return query
    select
        pc.id,
        pc.content,
        pc.metadata,
        1 - (pc.embedding <=> query_embedding) as similarity
    from product_catalog pc
    where pc.metadata @> filter
    order by pc.embedding <=> query_embedding
    limit match_count;
end;
$$;
