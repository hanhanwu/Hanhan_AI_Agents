-- supabase/migrations/007_fix_checkpoint_schema.sql
--
-- Fixes checkpoint tables to be compatible with langgraph-checkpoint-postgres v3.x.
-- Run this against existing databases that were set up with the old schema
-- (where checkpoint_writes had `value jsonb` instead of `blob bytea`).

-- Recreate checkpoint_writes with the correct blob BYTEA column
drop table if exists checkpoint_writes cascade;

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

create index idx_checkpoint_writes_thread_id on checkpoint_writes (thread_id);

-- Create checkpoint_blobs if it doesn't exist (new in v3.x)
create table if not exists checkpoint_blobs (
    thread_id     text  not null,
    checkpoint_ns text  not null default '',
    channel       text  not null,
    version       text  not null,
    type          text  not null,
    blob          bytea,
    primary key (thread_id, checkpoint_ns, channel, version)
);

alter table checkpoint_blobs enable row level security;

-- Create policy only if it doesn't already exist
do $$
begin
    if not exists (
        select 1 from pg_policies
        where tablename = 'checkpoint_blobs'
          and policyname = 'service role full access'
    ) then
        execute $policy$
            create policy "service role full access" on checkpoint_blobs
                for all
                using (auth.role() = 'service_role')
                with check (auth.role() = 'service_role')
        $policy$;
    end if;
end;
$$;

create index if not exists idx_checkpoint_blobs_thread_id on checkpoint_blobs (thread_id);

-- Ensure checkpoint_migrations exists (LangGraph tracks its own migrations here)
create table if not exists checkpoint_migrations (
    v integer primary key
);

-- Clear LangGraph's migration tracking so setup() re-applies from scratch
-- against the newly corrected tables.
truncate table checkpoint_migrations;
