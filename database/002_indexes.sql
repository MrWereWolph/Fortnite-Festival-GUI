-- ============================================================
-- FNFest GUI5 Database Indexes
-- File: database/002_indexes.sql
-- Target: Supabase / PostgreSQL
-- Purpose:
--   Search, filtering, sorting, imports, exports, and joins.
--
-- Notes:
--   - This assumes database/001_schema.sql has already run.
--   - These indexes are focused on GUI5 search behavior:
--       title search
--       artist search
--       BPM/key/mode filtering
--       genre/tag filtering
--       instrument difficulty filtering
--       import/upsert helpers
-- ============================================================


-- ============================================================
-- 1. Extensions
-- ============================================================
-- pg_trgm gives us fast partial/fuzzy text search with ILIKE
-- and similarity-style searches.
-- Example:
--   where title ilike '%bad%'
--   where artist_display ilike '%weeknd%'
-- ============================================================

create extension if not exists pg_trgm;


-- ============================================================
-- 2. Core Track Search Indexes
-- ============================================================

create index if not exists idx_tracks_epic_slug
on tracks (epic_slug);


create index if not exists idx_tracks_song_slug
on tracks (song_slug);


create index if not exists idx_tracks_title_trgm
on tracks using gin (title gin_trgm_ops);


create index if not exists idx_tracks_artist_display_trgm
on tracks using gin (artist_display gin_trgm_ops);


create index if not exists idx_tracks_album_title_trgm
on tracks using gin (album_title gin_trgm_ops);


create index if not exists idx_tracks_isrc
on tracks (isrc);


create index if not exists idx_tracks_sparks_song_id
on tracks (sparks_song_id);


create index if not exists idx_tracks_jam_code
on tracks (jam_code);


-- ============================================================
-- 3. Music Filtering Indexes
-- ============================================================

create index if not exists idx_tracks_bpm
on tracks (bpm);


create index if not exists idx_tracks_key_mode
on tracks (musical_key, mode);


create index if not exists idx_tracks_camelot_code
on tracks (camelot_code);


create index if not exists idx_tracks_bpm_camelot
on tracks (bpm, camelot_code);


create index if not exists idx_tracks_key_mode_bpm
on tracks (musical_key, mode, bpm);


create index if not exists idx_tracks_release_year
on tracks (release_year);


create index if not exists idx_tracks_duration_seconds
on tracks (duration_seconds);


create index if not exists idx_tracks_rating_code
on tracks (rating_code);


-- ============================================================
-- 4. Freshness / Import / Timeline Indexes
-- ============================================================

create index if not exists idx_tracks_active_date_desc
on tracks (active_date desc);


create index if not exists idx_tracks_new_until_desc
on tracks (new_until desc);


create index if not exists idx_tracks_last_modified_desc
on tracks (last_modified desc);


create index if not exists idx_tracks_first_seen_at_desc
on tracks (first_seen_at desc);


create index if not exists idx_tracks_last_seen_at_desc
on tracks (last_seen_at desc);


create index if not exists idx_tracks_last_import_batch_id
on tracks (last_import_batch_id);


create index if not exists idx_import_batches_imported_at_desc
on import_batches (imported_at desc);


create index if not exists idx_import_batches_source_last_modified_desc
on import_batches (source_last_modified desc);


create index if not exists idx_raw_tracks_import_batch_id
on raw_tracks (import_batch_id);


create index if not exists idx_raw_tracks_epic_slug
on raw_tracks (epic_slug);


-- ============================================================
-- 5. Artist Indexes
-- ============================================================

create index if not exists idx_artists_name_trgm
on artists using gin (name gin_trgm_ops);


create index if not exists idx_track_artists_track_id
on track_artists (track_id);


create index if not exists idx_track_artists_artist_id
on track_artists (artist_id);


create index if not exists idx_track_artists_artist_role
on track_artists (artist_role);


-- ============================================================
-- 6. Genre / Tag Indexes
-- ============================================================

create index if not exists idx_genres_genre_code
on genres (genre_code);


create index if not exists idx_genres_genre_label_trgm
on genres using gin (genre_label gin_trgm_ops);


create index if not exists idx_track_genres_track_id
on track_genres (track_id);


create index if not exists idx_track_genres_genre_id
on track_genres (genre_id);


create index if not exists idx_tags_tag_code
on tags (tag_code);


create index if not exists idx_tags_tag_label_trgm
on tags using gin (tag_label gin_trgm_ops);


create index if not exists idx_track_tags_track_id
on track_tags (track_id);


create index if not exists idx_track_tags_tag_id
on track_tags (tag_id);


-- ============================================================
-- 7. Asset Indexes
-- ============================================================

create index if not exists idx_track_assets_track_id
on track_assets (track_id);


create index if not exists idx_track_assets_asset_type
on track_assets (asset_type);


create index if not exists idx_track_assets_track_type
on track_assets (track_id, asset_type);


-- ============================================================
-- 8. Instrument Difficulty Indexes
-- ============================================================

create index if not exists idx_instrument_parts_group_sort
on instrument_parts (part_group, sort_order);


create index if not exists idx_track_difficulties_track_id
on track_difficulties (track_id);


create index if not exists idx_track_difficulties_part_code
on track_difficulties (part_code);


create index if not exists idx_track_difficulties_part_value
on track_difficulties (part_code, difficulty_value);


create index if not exists idx_track_difficulties_value
on track_difficulties (difficulty_value);


-- ============================================================
-- 9. Jam Stage Part Indexes
-- ============================================================

create index if not exists idx_track_jam_parts_track_id
on track_jam_parts (track_id);


create index if not exists idx_track_jam_parts_slot_code
on track_jam_parts (slot_code);


create index if not exists idx_track_jam_parts_instrument_name_trgm
on track_jam_parts using gin (instrument_name gin_trgm_ops);


-- ============================================================
-- 10. Audio Metadata / QI Indexes
-- ============================================================

create index if not exists idx_track_audio_metadata_qi_sid
on track_audio_metadata (qi_sid);


create index if not exists idx_track_audio_metadata_qi_pid
on track_audio_metadata (qi_pid);


create index if not exists idx_track_audio_metadata_stereo_id
on track_audio_metadata (stereo_id);


create index if not exists idx_track_audio_metadata_instrumental_id
on track_audio_metadata (instrumental_id);


create index if not exists idx_track_audio_metadata_preview_start_time
on track_audio_metadata (preview_start_time);


create index if not exists idx_track_audio_parts_track_id
on track_audio_parts (track_id);


create index if not exists idx_track_audio_parts_audio_part_code
on track_audio_parts (audio_part_code);


-- ============================================================
-- 11. User-Owned Track Indexes
-- ============================================================

create index if not exists idx_user_owned_tracks_user_id
on user_owned_tracks (user_id);


create index if not exists idx_user_owned_tracks_track_id
on user_owned_tracks (track_id);


create index if not exists idx_user_owned_tracks_user_owned
on user_owned_tracks (user_id, owned);


-- ============================================================
-- 12. Recipe / MixLab Indexes
-- ============================================================

create index if not exists idx_recipes_user_id
on recipes (user_id);


create index if not exists idx_recipes_is_public
on recipes (is_public);


create index if not exists idx_recipes_created_at_desc
on recipes (created_at desc);


create index if not exists idx_recipe_tracks_recipe_id
on recipe_tracks (recipe_id);


create index if not exists idx_recipe_tracks_track_id
on recipe_tracks (track_id);


create index if not exists idx_recipe_tracks_position
on recipe_tracks (recipe_id, position);


create index if not exists idx_recipe_stems_recipe_id
on recipe_stems (recipe_id);


create index if not exists idx_recipe_stems_track_id
on recipe_stems (track_id);


create index if not exists idx_recipe_stems_stem_part
on recipe_stems (stem_part);


create index if not exists idx_recipe_stems_stem_action
on recipe_stems (stem_action);


-- ============================================================
-- End of 002_indexes.sql
-- ============================================================