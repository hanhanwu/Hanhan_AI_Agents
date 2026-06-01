-- supabase/migrations/003_leads.sql
--
-- Stores lead / contact records that provide CRM context to the agents.
-- upsert_lead tool writes here; lookup_lead tool reads from here.

create table if not exists leads (
    id          bigserial primary key,
    email       text         not null unique,
    name        text,
    company     text,
    industry    text,

    -- BANT dimensions (updated by qualify_agent)
    budget      text,         -- 'high' | 'medium' | 'low'
    authority   text,         -- 'high' | 'medium' | 'low'
    need        text,         -- 'high' | 'medium' | 'low'
    timeline    text,         -- 'high' | 'medium' | 'low'

    lead_score  float default 0.0,
    notes       text,

    created_at  timestamptz not null default now(),
    updated_at  timestamptz not null default now()
);

-- Auto-update updated_at
create or replace function set_updated_at()
returns trigger language plpgsql as $$
begin
    new.updated_at = now();
    return new;
end;
$$;

create trigger leads_updated_at
    before update on leads
    for each row execute function set_updated_at();

-- Row Level Security (optional but recommended for production)
-- alter table leads enable row level security;
-- create policy "service role full access" on leads
--     using (auth.role() = 'service_role');
