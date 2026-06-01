-- supabase/migrations/001_langgraph_checkpoints.sql

-- Drop in reverse dependency order
drop table if exists checkpoint_writes cascade;
drop table if exists checkpoint_migrations cascade;
drop table if exists checkpoints cascade;

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

create table checkpoint_writes (
    thread_id     text    not null,
    checkpoint_ns text    not null default '',
    checkpoint_id text    not null,
    task_id       text    not null,
    idx           integer not null,
    channel       text    not null,
    type          text,
    value         jsonb,
    primary key (thread_id, checkpoint_ns, checkpoint_id, task_id, idx)
);

alter table checkpoint_writes enable row level security;

create policy "service role full access" on checkpoint_writes
    for all
    using (auth.role() = 'service_role')
    with check (auth.role() = 'service_role');

create table checkpoint_migrations (
    v integer primary key
);

alter table checkpoint_migrations enable row level security;

create policy "service role full access" on checkpoint_migrations
    for all
    using (auth.role() = 'service_role')
    with check (auth.role() = 'service_role');

-- Indexes for fast session lookup by thread_id
create index idx_checkpoints_thread_id       on checkpoints (thread_id);
create index idx_checkpoint_writes_thread_id on checkpoint_writes (thread_id);
