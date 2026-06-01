-- supabase/migrations/001_langgraph_checkpoints.sql
--
-- Schema compatible with langgraph-checkpoint-postgres v3.x.
-- LangGraph uses blob BYTEA (not value JSONB) and requires a
-- separate checkpoint_blobs table.

-- Drop in reverse dependency order
drop table if exists checkpoint_writes cascade;
drop table if exists checkpoint_blobs cascade;
drop table if exists checkpoint_migrations cascade;
drop table if exists checkpoints cascade;

create table checkpoint_migrations (
    v integer primary key
);

alter table checkpoint_migrations enable row level security;

create policy "service role full access" on checkpoint_migrations
    for all
    using (auth.role() = 'service_role')
    with check (auth.role() = 'service_role');

create table checkpoints (
    thread_id            text  not null,
    checkpoint_ns        text  not null default '',
    checkpoint_id        text  not null,
    parent_checkpoint_id text,
    type                 text,
    checkpoint           jsonb not null,
    metadata             jsonb not null default '{}',
    primary key (thread_id, checkpoint_ns, checkpoint_id)
);

alter table checkpoints enable row level security;

create policy "service role full access" on checkpoints
    for all
    using (auth.role() = 'service_role')
    with check (auth.role() = 'service_role');

-- checkpoint_blobs stores per-channel state blobs (v3.x)
create table checkpoint_blobs (
    thread_id     text  not null,
    checkpoint_ns text  not null default '',
    channel       text  not null,
    version       text  not null,
    type          text  not null,
    blob          bytea,
    primary key (thread_id, checkpoint_ns, channel, version)
);

alter table checkpoint_blobs enable row level security;

create policy "service role full access" on checkpoint_blobs
    for all
    using (auth.role() = 'service_role')
    with check (auth.role() = 'service_role');

-- checkpoint_writes uses blob BYTEA (not value JSONB) in v3.x
create table checkpoint_writes (
    thread_id     text    not null,
    checkpoint_ns text    not null default '',
    checkpoint_id text    not null,
    task_id       text    not null,
    task_path     text    not null default '',
    idx           integer not null,
    channel       text    not null,
    type          text,
    blob          bytea   not null,
    primary key (thread_id, checkpoint_ns, checkpoint_id, task_id, idx)
);

alter table checkpoint_writes enable row level security;

create policy "service role full access" on checkpoint_writes
    for all
    using (auth.role() = 'service_role')
    with check (auth.role() = 'service_role');

-- Indexes for fast session lookup by thread_id
create index idx_checkpoints_thread_id        on checkpoints (thread_id);
create index idx_checkpoint_blobs_thread_id   on checkpoint_blobs (thread_id);
create index idx_checkpoint_writes_thread_id  on checkpoint_writes (thread_id);
