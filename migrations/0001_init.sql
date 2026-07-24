-- Hello You — Supabase / Postgres schema
-- Apply via: psql $DIRECT_URL -f migrations/0001_init.sql
-- Or copy/paste into Supabase SQL editor.

create extension if not exists "pgcrypto";

-- Users
create table if not exists users (
    id               text primary key default gen_random_uuid()::text,
    email            text unique not null,
    full_name        text,
    avatar_url       text,
    hashed_password  text,
    provider         text not null default 'local',
    provider_sub     text,
    is_active        boolean not null default true,
    is_verified      boolean not null default false,
    role             text not null default 'user',
    created_at       timestamptz not null default now(),
    updated_at       timestamptz not null default now(),
    last_login_at    timestamptz
);
create index if not exists idx_users_provider_sub on users(provider_sub);

-- Investigations
create table if not exists investigations (
    id            text primary key default gen_random_uuid()::text,
    user_id       text not null references users(id) on delete cascade,
    kind          text not null,
    target        text not null,
    title         text,
    result        jsonb not null default '{}'::jsonb,
    risk_score    int,
    threat_level  text,
    is_favorite   boolean not null default false,
    notes         text,
    duration_ms   int,
    created_at    timestamptz not null default now()
);
create index if not exists idx_investigations_user on investigations(user_id);
create index if not exists idx_investigations_kind on investigations(kind);
create index if not exists idx_investigations_target on investigations(target);
create index if not exists idx_investigations_created on investigations(created_at desc);

-- Reports
create table if not exists reports (
    id              text primary key default gen_random_uuid()::text,
    user_id         text not null references users(id) on delete cascade,
    investigation_id text references investigations(id) on delete set null,
    title           text not null,
    format          text not null default 'pdf',
    content         jsonb not null default '{}'::jsonb,
    created_at      timestamptz not null default now()
);
create index if not exists idx_reports_user on reports(user_id);

-- Threat intel cache
create table if not exists threat_intel_cache (
    id              text primary key default gen_random_uuid()::text,
    indicator       text not null,
    indicator_type  text not null,
    source          text not null,
    risk_score      int not null default 0,
    data            jsonb not null default '{}'::jsonb,
    fetched_at      timestamptz not null default now(),
    expires_at      timestamptz not null
);
create index if not exists idx_threat_indicator on threat_intel_cache(indicator);
create index if not exists idx_threat_expires on threat_intel_cache(expires_at);

-- Audit log
create table if not exists audit_logs (
    id          text primary key default gen_random_uuid()::text,
    user_id     text references users(id) on delete set null,
    action      text not null,
    resource    text,
    ip_address  text,
    user_agent  text,
    extra       jsonb not null default '{}'::jsonb,
    created_at  timestamptz not null default now()
);
create index if not exists idx_audit_user on audit_logs(user_id);
create index if not exists idx_audit_action on audit_logs(action);
create index if not exists idx_audit_created on audit_logs(created_at desc);
