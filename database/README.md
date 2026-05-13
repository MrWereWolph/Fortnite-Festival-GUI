# FNFest GUI5 Database

This folder contains the SQL files for the FNFest GUI5 Supabase/PostgreSQL database.

FNFest GUI5 is a browser-accessible Fortnite Festival Jam Tracker inspired by the earlier GUI 4.0 project and Fortnite Jam Mixer. The database is designed to store as much useful Fortnite Festival track metadata as possible while keeping the data searchable, exportable, and normalized.

The schema is based around Epic's `spark-tracks` JSON structure, which contains root/page metadata, one object per track slug, nested `track` objects, genre arrays, gameplay tag arrays, instrument difficulty/intensity objects, asset URLs, Jam Stage instrument assignments, and embedded `qi` audio metadata.

---

## File Run Order

Run the files in this order:

```text
001_schema.sql
002_indexes.sql
003_views.sql
004_rls_policies.sql
```

Each file has a specific purpose.

---

## 001_schema.sql

Creates the core database tables.

This includes:

```text
import_batches
raw_tracks

tracks
artists
track_artists

genres
track_genres

tags
track_tags

track_assets

instrument_parts
track_difficulties

track_jam_parts

track_audio_metadata
track_audio_parts

user_owned_tracks

recipes
recipe_tracks
recipe_stems
```

The schema is split between two major layers:

```text
Raw layer:
Stores original Epic JSON for safety, auditing, and future-proofing.

Relational layer:
Stores clean searchable/exportable track data.
```

The raw layer matters because Epic may change, add, remove, or rename fields later. Keeping the original JSON gives GUI5 a recovery path.

---

## 002_indexes.sql

Creates performance indexes for common GUI5 searches and filters.

This includes indexes for:

```text
title search
artist search
album search
ISRC lookup
jam code lookup
BPM filtering
key/mode filtering
Camelot filtering
release year filtering
duration filtering
genre joins
tag joins
asset lookup
difficulty filtering
Jam Stage part lookup
audio metadata lookup
owned track lookup
recipe lookup
```

The file also enables the Postgres `pg_trgm` extension for faster partial/fuzzy text search.

Example use cases:

```sql
where title ilike '%bad%'
where artist_display ilike '%weeknd%'
where bpm between 120 and 130
where musical_key = 'A' and mode = 'Minor'
```

---

## 003_views.sql

Creates frontend/export-friendly views.

The frontend should prefer querying views instead of manually joining many normalized tables.

Important views:

```text
v_tracks_search
v_track_difficulties_flat
v_tracks_search_with_difficulties
v_track_jam_parts_flat
v_track_audio_metadata
v_artist_tracks
v_tracks_export
v_import_batch_summary
v_user_owned_tracks
v_recipe_tracks
```

The most important frontend view is:

```text
v_tracks_search
```

That view includes common search/display fields such as:

```text
title
artist_display
album_title
release_year
duration_seconds
bpm
musical_key
mode
camelot_code
rating_code
isrc
jam_code
album_art_url
music_data_url
lad_file_url
genres
tags
active_date
last_modified
```

For Main Stage difficulty display, use:

```text
v_track_difficulties_flat
```

For CSV exports, use:

```text
v_tracks_export
```

---

## 004_rls_policies.sql

Creates Row Level Security policies for Supabase.

The permission model is:

```text
Public catalog data:
Readable by anonymous and authenticated users.

Raw Epic JSON:
Readable by authenticated users for now.

Catalog writes/updates:
Service role only.

Owned songs:
Private to each authenticated user.

Recipes:
Private by default.
Public only when is_public = true.
```

Important rule:

```text
Never expose the Supabase service role key in frontend/browser code.
```

The browser should use the public/anon key. Import scripts, admin scripts, and protected Vercel server functions may use the service role key.

---

## Suggested Supabase Setup Flow

In Supabase:

1. Create a new Supabase project.
2. Open the SQL Editor.
3. Run `001_schema.sql`.
4. Run `002_indexes.sql`.
5. Run `003_views.sql`.
6. Run `004_rls_policies.sql`.
7. Confirm tables were created.
8. Confirm views were created.
9. Confirm RLS is enabled.
10. Run the import script later to populate the catalog.

---

## Local Development Notes

The database SQL files should be treated as source-controlled migration-style files.

Do not manually create tables in Supabase without also updating the SQL files in this folder.

Good workflow:

```text
Edit SQL file locally
Commit SQL file
Run SQL in Supabase
Test results
Commit follow-up fixes if needed
```

Bad workflow:

```text
Click around in Supabase
Manually change tables
Forget what changed
Lose reproducibility
```

---

## Data Import Plan

The future import script should:

```text
1. Fetch Epic spark-tracks JSON.
2. Create an import_batches row.
3. Store each track's raw JSON in raw_tracks.
4. Upsert clean track data into tracks.
5. Insert/update artists.
6. Insert track_artists relationships.
7. Insert/update genres.
8. Insert track_genres relationships.
9. Insert/update tags.
10. Insert track_tags relationships.
11. Insert/update track_assets.
12. Insert/update track_difficulties.
13. Insert/update track_jam_parts.
14. Parse qi JSON when available.
15. Insert/update track_audio_metadata.
16. Insert/update track_audio_parts.
```

---

## Export Plan

GUI5 should eventually support user-friendly downloads.

Recommended export formats:

```text
CSV:
Best first export format.
Useful for spreadsheet users.

JSON:
Useful for developers.
Can be clean normalized JSON or raw Epic JSON.

SQLite:
Useful long-term option for offline/power users.
Not a first-priority feature.
```

The first export target should be:

```text
v_tracks_export -> CSV
```

---

## Current Database Status

Current planned SQL files:

```text
[x] 001_schema.sql
[x] 002_indexes.sql
[x] 003_views.sql
[x] 004_rls_policies.sql
[ ] scripts/inspect_epic_tracks.py
[ ] scripts/import_epic_tracks.py
[ ] Supabase project created
[ ] Schema deployed to Supabase
[ ] Real Epic data imported
[ ] Frontend connected
[ ] Vercel deployed
```

---

## Notes for Future Development

Possible future additions:

```text
mix compatibility scores
saved MixLab decisions
recommendation history
public recipe sharing
user profile/settings table
download/export logs
API cache table
track change history
artist parser confidence scores
admin-only import dashboard
```

The current design intentionally separates normalized data from frontend views so GUI5 can evolve without constantly rewriting frontend queries.
