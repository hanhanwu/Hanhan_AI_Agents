-- supabase/migrations/005_update_embedding_dim.sql
--
-- Switch embeddings from OpenAI text-embedding-3-small (1536 dims)
-- to sentence-transformers/all-MiniLM-L6-v2 (384 dims).
-- Drops and recreates product_catalog and match_products.

drop table if exists product_catalog cascade;

create table product_catalog (
    id        bigserial      primary key,
    content   text           not null,
    metadata  jsonb          not null default '{}',
    embedding vector(384)    not null
);

alter table product_catalog enable row level security;

create policy "service role full access" on product_catalog
    for all
    using (auth.role() = 'service_role')
    with check (auth.role() = 'service_role');

create index product_catalog_embedding_idx
    on product_catalog
    using ivfflat (embedding vector_cosine_ops)
    with (lists = 100);

create or replace function match_products(
    query_embedding vector(384),
    match_count     int   default 5,
    filter          jsonb default '{}'
)
returns table (
    id         bigint,
    content    text,
    metadata   jsonb,
    similarity float
)
language plpgsql
security definer
set search_path = public
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
