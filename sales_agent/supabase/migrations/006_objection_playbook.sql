-- supabase/migrations/006_objection_playbook.sql
--
-- Objection playbook table for pgvector similarity search.
-- Used by the objection_agent to retrieve grounded rebuttals.
-- Embeddings: sentence-transformers/all-MiniLM-L6-v2 (384 dims)

drop table if exists objection_playbook cascade;

create table objection_playbook (
    id        bigserial    primary key,
    content   text         not null,
    metadata  jsonb        not null default '{}',
    embedding vector(384)  not null
);

alter table objection_playbook enable row level security;

create policy "service role full access" on objection_playbook
    for all
    using (auth.role() = 'service_role')
    with check (auth.role() = 'service_role');

create index objection_playbook_embedding_idx
    on objection_playbook
    using ivfflat (embedding vector_cosine_ops)
    with (lists = 100);

create or replace function match_objections(
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
        op.id,
        op.content,
        op.metadata,
        1 - (op.embedding <=> query_embedding) as similarity
    from objection_playbook op
    where op.metadata @> filter
    order by op.embedding <=> query_embedding
    limit match_count;
end;
$$;
