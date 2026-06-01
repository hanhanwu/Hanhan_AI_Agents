-- supabase/migrations/004_enable_rls.sql
--
-- Enable Row Level Security (RLS) on all tables.
-- Previous migrations were already applied without RLS, so this migration
-- retroactively locks them down. The service_role key used by the API server
-- bypasses RLS automatically; all other roles are denied.

-- checkpoints
alter table checkpoints enable row level security;

drop policy if exists "service role full access" on checkpoints;
create policy "service role full access" on checkpoints
    for all
    using (auth.role() = 'service_role')
    with check (auth.role() = 'service_role');

-- checkpoint_writes
alter table checkpoint_writes enable row level security;

drop policy if exists "service role full access" on checkpoint_writes;
create policy "service role full access" on checkpoint_writes
    for all
    using (auth.role() = 'service_role')
    with check (auth.role() = 'service_role');

-- checkpoint_migrations
alter table checkpoint_migrations enable row level security;

drop policy if exists "service role full access" on checkpoint_migrations;
create policy "service role full access" on checkpoint_migrations
    for all
    using (auth.role() = 'service_role')
    with check (auth.role() = 'service_role');

-- product_catalog
alter table product_catalog enable row level security;

drop policy if exists "service role full access" on product_catalog;
create policy "service role full access" on product_catalog
    for all
    using (auth.role() = 'service_role')
    with check (auth.role() = 'service_role');

-- leads
alter table leads enable row level security;

drop policy if exists "service role full access" on leads;
create policy "service role full access" on leads
    for all
    using (auth.role() = 'service_role')
    with check (auth.role() = 'service_role');
