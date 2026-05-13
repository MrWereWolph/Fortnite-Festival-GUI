-- ============================================================
-- FNFest GUI5 Database Schema
-- File: database/001_schema.sql
-- Target: Supabase / PostgreSQL
-- Purpose:
--   Core relational schema for Fortnite Festival track data.
--
-- Notes:
--   - Raw Epic JSON is preserved first.
--   - Clean relational tables are used for search/export/UI.
--   - Indexes, views, and RLS policies should be kept in
--     separate files:
--       002_indexes.sql
--       003_views.sql
--       004_rls_policies.sql
-- ============================================================


-- ============================================================
-- 1. Source / Import Tracking
-- ============================================================

create table if not exists import_batches (
    import_batch_id bigserial primary key,

    source_name text not null default 'epic_spark_tracks',
    source_url text not null,

    source_title text,
    source_locale text,
    source_template_name text,

    source_active_date timestamptz,
    source_last_modified timestamptz,

    imported_at timestamptz not null default now(),
    track_count integer,

    notes text
);


create table if not exists raw_tracks (
    raw_track_id bigserial primary key,

    import_batch_id bigint not null
        references import_batches(import_batch_id)
        on delete cascade,

    epic_slug text not null,

    page_title text,
    page_no_index boolean,
    page_active_date timestamptz,
    page_last_modified timestamptz,
    page_locale text,
    page_template_name text,

    raw_page_json jsonb not null,
    raw_track_json jsonb,

    created_at timestamptz not null default now(),

    constraint uq_raw_tracks_batch_slug
        unique (import_batch_id, epic_slug)
);


-- ============================================================
-- 2. Core Catalog Tables
-- ============================================================

create table if not exists tracks (
    track_id bigserial primary key,

    -- Epic/CMS identifiers
    epic_slug text not null unique,
    song_slug text,
    song_uuid uuid,
    sparks_song_id text,

    -- Main display metadata
    title text not null,
    artist_display text,
    album_title text,

    -- Music metadata
    release_year integer,
    duration_seconds integer,
    bpm integer,
    musical_key text,
    mode text,
    camelot_code text,

    -- Rating / identifiers
    rating_code text,
    isrc text,
    jam_code text,

    -- Misc Epic fields
    mmo integer,
    ag text,
    sm text,

    -- Page metadata
    no_index boolean,
    active_date timestamptz,
    new_until timestamptz,
    last_modified timestamptz,
    locale text,
    template_name text,

    -- Import tracking
    first_seen_at timestamptz not null default now(),
    last_seen_at timestamptz not null default now(),

    last_import_batch_id bigint
        references import_batches(import_batch_id)
        on delete set null,

    -- Safety checks
    constraint chk_tracks_release_year
        check (release_year is null or release_year between 1900 and 2100),

    constraint chk_tracks_duration_seconds
        check (duration_seconds is null or duration_seconds > 0),

    constraint chk_tracks_bpm
        check (bpm is null or bpm between 1 and 400)
);


-- ============================================================
-- 3. Artists
-- ============================================================

create table if not exists artists (
    artist_id bigserial primary key,

    name text not null unique,

    created_at timestamptz not null default now()
);


create table if not exists track_artists (
    track_id bigint not null
        references tracks(track_id)
        on delete cascade,

    artist_id bigint not null
        references artists(artist_id)
        on delete restrict,

    artist_order integer not null default 1,

    -- Examples:
    -- primary
    -- featured
    -- collaborator
    -- unknown
    artist_role text not null default 'primary',

    -- Stores the original artist string segment if parsed.
    source_text text,

    primary key (track_id, artist_id, artist_role)
);


-- ============================================================
-- 4. Genres and Gameplay Tags
-- ============================================================

create table if not exists genres (
    genre_id bigserial primary key,

    genre_code text not null unique,
    genre_label text,

    created_at timestamptz not null default now()
);


create table if not exists track_genres (
    track_id bigint not null
        references tracks(track_id)
        on delete cascade,

    genre_id bigint not null
        references genres(genre_id)
        on delete restrict,

    primary key (track_id, genre_id)
);


create table if not exists tags (
    tag_id bigserial primary key,

    tag_code text not null unique,
    tag_label text,

    created_at timestamptz not null default now()
);


create table if not exists track_tags (
    track_id bigint not null
        references tracks(track_id)
        on delete cascade,

    tag_id bigint not null
        references tags(tag_id)
        on delete restrict,

    primary key (track_id, tag_id)
);


-- ============================================================
-- 5. Track Assets / URLs
-- ============================================================

create table if not exists track_assets (
    asset_id bigserial primary key,

    track_id bigint not null
        references tracks(track_id)
        on delete cascade,

    -- Examples:
    -- album_art
    -- music_data
    -- lad_file
    -- audio_preview
    asset_type text not null,

    url text not null,

    created_at timestamptz not null default now(),

    constraint uq_track_assets_track_type_url
        unique (track_id, asset_type, url)
);


-- ============================================================
-- 6. Instrument Parts and Difficulties / Intensities
-- ============================================================

create table if not exists instrument_parts (
    part_code text primary key,

    part_name text not null,

    -- Examples:
    -- main_stage
    -- pro
    -- jam_stage
    -- band
    part_group text,

    sort_order integer
);


create table if not exists track_difficulties (
    track_id bigint not null
        references tracks(track_id)
        on delete cascade,

    part_code text not null
        references instrument_parts(part_code)
        on delete restrict,

    difficulty_value integer not null,

    primary key (track_id, part_code),

    -- Epic sometimes uses 99 in the intensity object, so do not
    -- restrict this to only 0-6.
    constraint chk_track_difficulties_value
        check (difficulty_value between 0 and 99)
);


-- ============================================================
-- 7. Jam Stage Instrument Assignments
-- ============================================================

create table if not exists track_jam_parts (
    track_id bigint not null
        references tracks(track_id)
        on delete cascade,

    -- Examples from Epic:
    -- siv = vocals slot
    -- sib = bass slot
    -- sid = drums slot
    -- sig = lead/guitar slot
    slot_code text not null,

    instrument_name text,

    primary key (track_id, slot_code)
);


-- ============================================================
-- 8. Parsed QI / Audio Metadata
-- ============================================================

create table if not exists track_audio_metadata (
    track_id bigint primary key
        references tracks(track_id)
        on delete cascade,

    qi_sid uuid,
    qi_pid uuid,
    stereo_id uuid,
    instrumental_id uuid,

    qi_title text,
    preview_start_time numeric,

    raw_qi jsonb
);


create table if not exists track_audio_parts (
    track_id bigint not null
        references tracks(track_id)
        on delete cascade,

    -- Examples from qi.tracks:
    -- ds, bs, gs, vs, fs
    audio_part_code text not null,

    channels text[],
    volumes numeric[],

    primary key (track_id, audio_part_code)
);


-- ============================================================
-- 9. User-Owned Tracks
-- ============================================================
-- Supabase auth user IDs are UUIDs. We will add RLS later.
-- ============================================================

create table if not exists user_owned_tracks (
    user_id uuid not null,

    track_id bigint not null
        references tracks(track_id)
        on delete cascade,

    owned boolean not null default true,

    acquired_at timestamptz,
    notes text,

    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now(),

    primary key (user_id, track_id)
);


-- ============================================================
-- 10. Recipes / Setlists / MixLab Foundation
-- ============================================================

create table if not exists recipes (
    recipe_id bigserial primary key,

    user_id uuid not null,

    recipe_name text not null,
    description text,

    is_public boolean not null default false,

    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now()
);


create table if not exists recipe_tracks (
    recipe_id bigint not null
        references recipes(recipe_id)
        on delete cascade,

    track_id bigint not null
        references tracks(track_id)
        on delete cascade,

    position integer not null,

    role_notes text,

    primary key (recipe_id, position),

    constraint uq_recipe_tracks_recipe_track
        unique (recipe_id, track_id)
);


create table if not exists recipe_stems (
    recipe_id bigint not null
        references recipes(recipe_id)
        on delete cascade,

    track_id bigint not null
        references tracks(track_id)
        on delete cascade,

    -- Examples:
    -- drums
    -- bass
    -- lead
    -- vocals
    stem_part text not null,

    -- Examples:
    -- accept
    -- reject
    -- exclude
    stem_action text not null,

    primary key (recipe_id, track_id, stem_part),

    constraint chk_recipe_stems_action
        check (stem_action in ('accept', 'reject', 'exclude'))
);


-- ============================================================
-- 11. Seed Instrument Parts
-- ============================================================
-- We include this in 001_schema.sql for now because difficulties
-- depend on these values existing during import.
-- ============================================================

insert into instrument_parts (part_code, part_name, part_group, sort_order)
values
    ('bd', 'Band', 'band', 10),

    ('vl', 'Vocals', 'main_stage', 20),
    ('gr', 'Guitar', 'main_stage', 30),
    ('ba', 'Bass', 'main_stage', 40),
    ('ds', 'Drums', 'main_stage', 50),

    ('pg', 'Pro Guitar', 'pro', 60),
    ('pb', 'Pro Bass', 'pro', 70),
    ('pd', 'Pro Drums', 'pro', 80)
on conflict (part_code) do update
set
    part_name = excluded.part_name,
    part_group = excluded.part_group,
    sort_order = excluded.sort_order;


-- ============================================================
-- End of 001_schema.sql
-- ============================================================