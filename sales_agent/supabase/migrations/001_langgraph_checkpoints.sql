-- supabase/migrations/001_langgraph_checkpoints.sql
--
-- LangGraph's AsyncPostgresSaver.setup() creates these tables automatically,
-- but defining them here makes the schema explicit and version-controlled.
-- Safe to run even if the tables already exist.

create table if not exists checkpoints (
    thread_id    text   not null,
    checkpoint_ns text  not null default '',
    checkpoint_id text  not null,
    parent_checkpoint_id text,
    type         text,
    checkpoint    jsonb  not null,
    metadata      jsonb  not null default '{}',
    primary key (thread_id, checkpoint_ns, checkpoint_id)
);

create table if not exists checkpoint_writes (
    thread_id    text   not null,
    checkpoint_ns text  not null default '',
    checkpoint_id text  not null,
    task_id      text   not null,
    idx          integer not null,
    channel      text   not null,
    type         text,
    value        jsonb,
    primary key (thread_id, checkpoint_ns, checkpoint_id, task_id, idx)
);

create table if not exists checkpoint_migrations (
    v integer primary key
);

-- Index for fast session lookup by thread_id
create index if not exists idx_checkpoints_thread_id on checkpoints (thread_id);
create index if not exists idx_checkpoint_writes_thread_id on checkpoint_writes (thread_id);
