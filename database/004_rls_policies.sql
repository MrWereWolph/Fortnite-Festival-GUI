-- ============================================================
-- FNFest GUI5 Row Level Security Policies
-- File: database/004_rls_policies.sql
-- Target: Supabase / PostgreSQL
-- Purpose:
--   Public read access for catalog data.
--   User-private read/write access for owned tracks and recipes.
--
-- Notes:
--   - This assumes 001_schema.sql, 002_indexes.sql, and
--     003_views.sql have already run.
--
--   - Public catalog tables are readable by anon/authenticated users.
--
--   - Catalog writes should be performed only by trusted server-side
--     code using the Supabase service role key.
--
--   - The browser should never receive the service role key.
--
--   - User tables use auth.uid() to restrict rows to the current user.
-- ============================================================


-- ============================================================
-- 1. Enable RLS on Catalog Tables
-- ============================================================

alter table import_batches enable row level security;
alter table raw_tracks enable row level security;

alter table tracks enable row level security;
alter table artists enable row level security;
alter table track_artists enable row level security;

alter table genres enable row level security;
alter table track_genres enable row level security;

alter table tags enable row level security;
alter table track_tags enable row level security;

alter table track_assets enable row level security;

alter table instrument_parts enable row level security;
alter table track_difficulties enable row level security;

alter table track_jam_parts enable row level security;

alter table track_audio_metadata enable row level security;
alter table track_audio_parts enable row level security;


-- ============================================================
-- 2. Enable RLS on User Tables
-- ============================================================

alter table user_owned_tracks enable row level security;
alter table recipes enable row level security;
alter table recipe_tracks enable row level security;
alter table recipe_stems enable row level security;


-- ============================================================
-- 3. Public Read Policies for Catalog Tables
-- ============================================================
-- GUI5's catalog is public/read-only to normal users.
-- No insert/update/delete policies are created for these tables.
--
-- Trusted imports should use the service role key from a secure
-- backend/admin environment.
-- ============================================================

drop policy if exists "Public can read import batches" on import_batches;
create policy "Public can read import batches"
on import_batches
for select
to anon, authenticated
using (true);


-- Raw tracks contain original Epic JSON.
-- For now, keep this locked down from public users.
-- We can expose raw/developer export later through a controlled API.
drop policy if exists "Authenticated can read raw tracks" on raw_tracks;
create policy "Authenticated can read raw tracks"
on raw_tracks
for select
to authenticated
using (true);


drop policy if exists "Public can read tracks" on tracks;
create policy "Public can read tracks"
on tracks
for select
to anon, authenticated
using (true);


drop policy if exists "Public can read artists" on artists;
create policy "Public can read artists"
on artists
for select
to anon, authenticated
using (true);


drop policy if exists "Public can read track artists" on track_artists;
create policy "Public can read track artists"
on track_artists
for select
to anon, authenticated
using (true);


drop policy if exists "Public can read genres" on genres;
create policy "Public can read genres"
on genres
for select
to anon, authenticated
using (true);


drop policy if exists "Public can read track genres" on track_genres;
create policy "Public can read track genres"
on track_genres
for select
to anon, authenticated
using (true);


drop policy if exists "Public can read tags" on tags;
create policy "Public can read tags"
on tags
for select
to anon, authenticated
using (true);


drop policy if exists "Public can read track tags" on track_tags;
create policy "Public can read track tags"
on track_tags
for select
to anon, authenticated
using (true);


drop policy if exists "Public can read track assets" on track_assets;
create policy "Public can read track assets"
on track_assets
for select
to anon, authenticated
using (true);


drop policy if exists "Public can read instrument parts" on instrument_parts;
create policy "Public can read instrument parts"
on instrument_parts
for select
to anon, authenticated
using (true);


drop policy if exists "Public can read track difficulties" on track_difficulties;
create policy "Public can read track difficulties"
on track_difficulties
for select
to anon, authenticated
using (true);


drop policy if exists "Public can read track jam parts" on track_jam_parts;
create policy "Public can read track jam parts"
on track_jam_parts
for select
to anon, authenticated
using (true);


drop policy if exists "Public can read track audio metadata" on track_audio_metadata;
create policy "Public can read track audio metadata"
on track_audio_metadata
for select
to anon, authenticated
using (true);


drop policy if exists "Public can read track audio parts" on track_audio_parts;
create policy "Public can read track audio parts"
on track_audio_parts
for select
to anon, authenticated
using (true);


-- ============================================================
-- 4. User-Owned Tracks Policies
-- ============================================================

drop policy if exists "Users can read own owned tracks" on user_owned_tracks;
create policy "Users can read own owned tracks"
on user_owned_tracks
for select
to authenticated
using (
    (select auth.uid()) = user_id
);


drop policy if exists "Users can insert own owned tracks" on user_owned_tracks;
create policy "Users can insert own owned tracks"
on user_owned_tracks
for insert
to authenticated
with check (
    (select auth.uid()) = user_id
);


drop policy if exists "Users can update own owned tracks" on user_owned_tracks;
create policy "Users can update own owned tracks"
on user_owned_tracks
for update
to authenticated
using (
    (select auth.uid()) = user_id
)
with check (
    (select auth.uid()) = user_id
);


drop policy if exists "Users can delete own owned tracks" on user_owned_tracks;
create policy "Users can delete own owned tracks"
on user_owned_tracks
for delete
to authenticated
using (
    (select auth.uid()) = user_id
);


-- ============================================================
-- 5. Recipe Policies
-- ============================================================
-- Users can manage their own recipes.
-- Public recipes can be read by anyone.
-- ============================================================

drop policy if exists "Public can read public recipes" on recipes;
create policy "Public can read public recipes"
on recipes
for select
to anon, authenticated
using (
    is_public = true
);


drop policy if exists "Users can read own recipes" on recipes;
create policy "Users can read own recipes"
on recipes
for select
to authenticated
using (
    (select auth.uid()) = user_id
);


drop policy if exists "Users can insert own recipes" on recipes;
create policy "Users can insert own recipes"
on recipes
for insert
to authenticated
with check (
    (select auth.uid()) = user_id
);


drop policy if exists "Users can update own recipes" on recipes;
create policy "Users can update own recipes"
on recipes
for update
to authenticated
using (
    (select auth.uid()) = user_id
)
with check (
    (select auth.uid()) = user_id
);


drop policy if exists "Users can delete own recipes" on recipes;
create policy "Users can delete own recipes"
on recipes
for delete
to authenticated
using (
    (select auth.uid()) = user_id
);


-- ============================================================
-- 6. Recipe Tracks Policies
-- ============================================================
-- recipe_tracks inherits ownership through recipes.
-- Public recipe tracks are visible when the parent recipe is public.
-- ============================================================

drop policy if exists "Public can read public recipe tracks" on recipe_tracks;
create policy "Public can read public recipe tracks"
on recipe_tracks
for select
to anon, authenticated
using (
    exists (
        select 1
        from recipes r
        where r.recipe_id = recipe_tracks.recipe_id
          and r.is_public = true
    )
);


drop policy if exists "Users can read own recipe tracks" on recipe_tracks;
create policy "Users can read own recipe tracks"
on recipe_tracks
for select
to authenticated
using (
    exists (
        select 1
        from recipes r
        where r.recipe_id = recipe_tracks.recipe_id
          and r.user_id = (select auth.uid())
    )
);


drop policy if exists "Users can insert own recipe tracks" on recipe_tracks;
create policy "Users can insert own recipe tracks"
on recipe_tracks
for insert
to authenticated
with check (
    exists (
        select 1
        from recipes r
        where r.recipe_id = recipe_tracks.recipe_id
          and r.user_id = (select auth.uid())
    )
);


drop policy if exists "Users can update own recipe tracks" on recipe_tracks;
create policy "Users can update own recipe tracks"
on recipe_tracks
for update
to authenticated
using (
    exists (
        select 1
        from recipes r
        where r.recipe_id = recipe_tracks.recipe_id
          and r.user_id = (select auth.uid())
    )
)
with check (
    exists (
        select 1
        from recipes r
        where r.recipe_id = recipe_tracks.recipe_id
          and r.user_id = (select auth.uid())
    )
);


drop policy if exists "Users can delete own recipe tracks" on recipe_tracks;
create policy "Users can delete own recipe tracks"
on recipe_tracks
for delete
to authenticated
using (
    exists (
        select 1
        from recipes r
        where r.recipe_id = recipe_tracks.recipe_id
          and r.user_id = (select auth.uid())
    )
);


-- ============================================================
-- 7. Recipe Stems Policies
-- ============================================================
-- recipe_stems also inherits ownership through recipes.
-- ============================================================

drop policy if exists "Public can read public recipe stems" on recipe_stems;
create policy "Public can read public recipe stems"
on recipe_stems
for select
to anon, authenticated
using (
    exists (
        select 1
        from recipes r
        where r.recipe_id = recipe_stems.recipe_id
          and r.is_public = true
    )
);


drop policy if exists "Users can read own recipe stems" on recipe_stems;
create policy "Users can read own recipe stems"
on recipe_stems
for select
to authenticated
using (
    exists (
        select 1
        from recipes r
        where r.recipe_id = recipe_stems.recipe_id
          and r.user_id = (select auth.uid())
    )
);


drop policy if exists "Users can insert own recipe stems" on recipe_stems;
create policy "Users can insert own recipe stems"
on recipe_stems
for insert
to authenticated
with check (
    exists (
        select 1
        from recipes r
        where r.recipe_id = recipe_stems.recipe_id
          and r.user_id = (select auth.uid())
    )
);


drop policy if exists "Users can update own recipe stems" on recipe_stems;
create policy "Users can update own recipe stems"
on recipe_stems
for update
to authenticated
using (
    exists (
        select 1
        from recipes r
        where r.recipe_id = recipe_stems.recipe_id
          and r.user_id = (select auth.uid())
    )
)
with check (
    exists (
        select 1
        from recipes r
        where r.recipe_id = recipe_stems.recipe_id
          and r.user_id = (select auth.uid())
    )
);


drop policy if exists "Users can delete own recipe stems" on recipe_stems;
create policy "Users can delete own recipe stems"
on recipe_stems
for delete
to authenticated
using (
    exists (
        select 1
        from recipes r
        where r.recipe_id = recipe_stems.recipe_id
          and r.user_id = (select auth.uid())
    )
);


-- ============================================================
-- End of 004_rls_policies.sql
-- ============================================================