-- ============================================================
-- FNFest GUI5 Database Views
-- File: database/003_views.sql
-- Target: Supabase / PostgreSQL
-- Purpose:
--   Frontend/export-friendly views over the normalized schema.
--
-- Notes:
--   - This assumes 001_schema.sql and 002_indexes.sql have run.
--   - These views are read-only query surfaces for the app.
--   - RLS/security policies will be handled in 004_rls_policies.sql.
-- ============================================================


-- ============================================================
-- 1. Track Search View
-- ============================================================
-- Main frontend search view.
--
-- Includes:
--   - core track metadata
--   - cover art URL
--   - music data URL
--   - LAD file URL
--   - genres as text[]
--   - gameplay tags as text[]
--
-- This is the view the search page should use first.
-- ============================================================

create or replace view v_tracks_search as
select
    t.track_id,
    t.epic_slug,
    t.song_slug,
    t.song_uuid,
    t.sparks_song_id,

    t.title,
    t.artist_display,
    t.album_title,

    t.release_year,
    t.duration_seconds,
    t.bpm,
    t.musical_key,
    t.mode,
    t.camelot_code,

    t.rating_code,
    t.isrc,
    t.jam_code,

    t.mmo,
    t.ag,
    t.sm,

    t.no_index,
    t.active_date,
    t.new_until,
    t.last_modified,
    t.locale,
    t.template_name,

    t.first_seen_at,
    t.last_seen_at,

    max(case when ta.asset_type = 'album_art' then ta.url end) as album_art_url,
    max(case when ta.asset_type = 'music_data' then ta.url end) as music_data_url,
    max(case when ta.asset_type = 'lad_file' then ta.url end) as lad_file_url,

    coalesce(
        array_remove(array_agg(distinct g.genre_code), null),
        array[]::text[]
    ) as genres,

    coalesce(
        array_remove(array_agg(distinct tg.tag_code), null),
        array[]::text[]
    ) as tags

from tracks t
left join track_assets ta
    on ta.track_id = t.track_id
left join track_genres tgr
    on tgr.track_id = t.track_id
left join genres g
    on g.genre_id = tgr.genre_id
left join track_tags ttg
    on ttg.track_id = t.track_id
left join tags tg
    on tg.tag_id = ttg.tag_id
group by
    t.track_id;


-- ============================================================
-- 2. Flattened Difficulty View
-- ============================================================
-- Makes Main Stage/pro difficulty data easy for frontend cards.
--
-- Epic's "in" object gives codes like:
--   bd, vl, gr, ba, ds, pg, pb, pd
--
-- We store those normalized in track_difficulties, but this view
-- flattens them for easy display/export.
-- ============================================================

create or replace view v_track_difficulties_flat as
select
    t.track_id,
    t.epic_slug,
    t.title,
    t.artist_display,

    max(case when td.part_code = 'bd' then td.difficulty_value end) as band,
    max(case when td.part_code = 'vl' then td.difficulty_value end) as vocals,
    max(case when td.part_code = 'gr' then td.difficulty_value end) as guitar,
    max(case when td.part_code = 'ba' then td.difficulty_value end) as bass,
    max(case when td.part_code = 'ds' then td.difficulty_value end) as drums,

    max(case when td.part_code = 'pg' then td.difficulty_value end) as pro_guitar,
    max(case when td.part_code = 'pb' then td.difficulty_value end) as pro_bass,
    max(case when td.part_code = 'pd' then td.difficulty_value end) as pro_drums

from tracks t
left join track_difficulties td
    on td.track_id = t.track_id
group by
    t.track_id,
    t.epic_slug,
    t.title,
    t.artist_display;


-- ============================================================
-- 3. Track Search + Difficulty View
-- ============================================================
-- Convenience view for pages that need both metadata and
-- instrument difficulty values.
-- ============================================================

create or replace view v_tracks_search_with_difficulties as
select
    s.*,

    d.band,
    d.vocals,
    d.guitar,
    d.bass,
    d.drums,
    d.pro_guitar,
    d.pro_bass,
    d.pro_drums

from v_tracks_search s
left join v_track_difficulties_flat d
    on d.track_id = s.track_id;


-- ============================================================
-- 4. Jam Parts Flat View
-- ============================================================
-- Flattens siv/sib/sid/sig-style Jam Stage instrument assignments.
-- ============================================================

create or replace view v_track_jam_parts_flat as
select
    t.track_id,
    t.epic_slug,
    t.title,
    t.artist_display,

    max(case when tjp.slot_code = 'siv' then tjp.instrument_name end) as jam_vocals,
    max(case when tjp.slot_code = 'sib' then tjp.instrument_name end) as jam_bass,
    max(case when tjp.slot_code = 'sid' then tjp.instrument_name end) as jam_drums,
    max(case when tjp.slot_code = 'sig' then tjp.instrument_name end) as jam_lead

from tracks t
left join track_jam_parts tjp
    on tjp.track_id = t.track_id
group by
    t.track_id,
    t.epic_slug,
    t.title,
    t.artist_display;


-- ============================================================
-- 5. Audio Metadata View
-- ============================================================
-- Frontend-friendly access to parsed qi data.
-- ============================================================

create or replace view v_track_audio_metadata as
select
    t.track_id,
    t.epic_slug,
    t.title,
    t.artist_display,

    tam.qi_sid,
    tam.qi_pid,
    tam.stereo_id,
    tam.instrumental_id,
    tam.qi_title,
    tam.preview_start_time,

    coalesce(
        jsonb_agg(
            jsonb_build_object(
                'audio_part_code', tap.audio_part_code,
                'channels', tap.channels,
                'volumes', tap.volumes
            )
            order by tap.audio_part_code
        ) filter (where tap.audio_part_code is not null),
        '[]'::jsonb
    ) as audio_parts

from tracks t
left join track_audio_metadata tam
    on tam.track_id = t.track_id
left join track_audio_parts tap
    on tap.track_id = t.track_id
group by
    t.track_id,
    t.epic_slug,
    t.title,
    t.artist_display,
    tam.qi_sid,
    tam.qi_pid,
    tam.stereo_id,
    tam.instrumental_id,
    tam.qi_title,
    tam.preview_start_time;


-- ============================================================
-- 6. Artist Detail View
-- ============================================================
-- Useful for artist pages and artist search.
-- ============================================================

create or replace view v_artist_tracks as
select
    a.artist_id,
    a.name as artist_name,

    ta.artist_role,
    ta.artist_order,
    ta.source_text,

    t.track_id,
    t.epic_slug,
    t.title,
    t.artist_display,
    t.album_title,
    t.release_year,
    t.bpm,
    t.musical_key,
    t.mode,
    t.camelot_code,
    t.duration_seconds,
    t.rating_code,
    t.isrc,
    t.jam_code,
    t.active_date,
    t.last_modified

from artists a
join track_artists ta
    on ta.artist_id = a.artist_id
join tracks t
    on t.track_id = ta.track_id;


-- ============================================================
-- 7. Public CSV Export View
-- ============================================================
-- Cleaner, spreadsheet-friendly track catalog export.
-- This intentionally avoids raw JSON and user data.
-- ============================================================

create or replace view v_tracks_export as
select
    s.epic_slug,
    s.song_slug,
    s.sparks_song_id,

    s.title,
    s.artist_display,
    s.album_title,

    s.release_year,
    s.duration_seconds,
    s.bpm,
    s.musical_key,
    s.mode,
    s.camelot_code,

    s.rating_code,
    s.isrc,
    s.jam_code,

    array_to_string(s.genres, '|') as genres,
    array_to_string(s.tags, '|') as tags,

    d.band,
    d.vocals,
    d.guitar,
    d.bass,
    d.drums,
    d.pro_guitar,
    d.pro_bass,
    d.pro_drums,

    j.jam_vocals,
    j.jam_bass,
    j.jam_drums,
    j.jam_lead,

    s.album_art_url,
    s.music_data_url,
    s.lad_file_url,

    s.active_date,
    s.new_until,
    s.last_modified,
    s.first_seen_at,
    s.last_seen_at

from v_tracks_search s
left join v_track_difficulties_flat d
    on d.track_id = s.track_id
left join v_track_jam_parts_flat j
    on j.track_id = s.track_id;


-- ============================================================
-- 8. Import Batch Summary View
-- ============================================================

create or replace view v_import_batch_summary as
select
    ib.import_batch_id,
    ib.source_name,
    ib.source_url,
    ib.source_title,
    ib.source_locale,
    ib.source_template_name,
    ib.source_active_date,
    ib.source_last_modified,
    ib.imported_at,
    ib.track_count,
    count(rt.raw_track_id) as raw_track_rows,
    ib.notes

from import_batches ib
left join raw_tracks rt
    on rt.import_batch_id = ib.import_batch_id
group by
    ib.import_batch_id;


-- ============================================================
-- 9. Owned Tracks View
-- ============================================================
-- This is useful once Supabase Auth/RLS is active.
-- It still does not expose other users' data safely until RLS
-- policies are added in 004_rls_policies.sql.
-- ============================================================

create or replace view v_user_owned_tracks as
select
    uot.user_id,
    uot.track_id,
    uot.owned,
    uot.acquired_at,
    uot.notes,
    uot.created_at,
    uot.updated_at,

    s.epic_slug,
    s.title,
    s.artist_display,
    s.album_title,
    s.release_year,
    s.duration_seconds,
    s.bpm,
    s.musical_key,
    s.mode,
    s.camelot_code,
    s.rating_code,
    s.isrc,
    s.jam_code,
    s.album_art_url,
    s.genres,
    s.tags

from user_owned_tracks uot
join v_tracks_search s
    on s.track_id = uot.track_id;


-- ============================================================
-- 10. Recipe Detail View
-- ============================================================

create or replace view v_recipe_tracks as
select
    r.recipe_id,
    r.user_id,
    r.recipe_name,
    r.description,
    r.is_public,
    r.created_at as recipe_created_at,
    r.updated_at as recipe_updated_at,

    rt.position,
    rt.role_notes,

    s.track_id,
    s.epic_slug,
    s.title,
    s.artist_display,
    s.album_title,
    s.release_year,
    s.duration_seconds,
    s.bpm,
    s.musical_key,
    s.mode,
    s.camelot_code,
    s.rating_code,
    s.isrc,
    s.jam_code,
    s.album_art_url,
    s.genres,
    s.tags

from recipes r
join recipe_tracks rt
    on rt.recipe_id = r.recipe_id
join v_tracks_search s
    on s.track_id = rt.track_id;


-- ============================================================
-- End of 003_views.sql
-- ============================================================