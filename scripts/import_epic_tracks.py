#!/usr/bin/env python3
"""
FNFest GUI5 - Batched Epic Spark Tracks Supabase Importer

Purpose:
    Fetch Epic's spark-tracks JSON, preserve raw JSON, and upsert normalized
    Fortnite Festival catalog data into Supabase/Postgres with far fewer
    API requests than the original one-track-at-a-time importer.

Required .env values:
    SUPABASE_URL=
    SUPABASE_SERVICE_ROLE_KEY=

Important:
    Never expose the service role key in frontend/browser code.
"""

from __future__ import annotations

import json
import os
import re
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any
from urllib.parse import urlparse

import requests
from dotenv import load_dotenv
from supabase import Client, create_client


EPIC_SPARK_TRACKS_URL = (
    "https://fortnitecontent-website-prod07.ol.epicgames.com/"
    "content/api/pages/fortnite-game/spark-tracks"
)

ROOT_METADATA_FIELDS = {
    "_title",
    "_noIndex",
    "_activeDate",
    "lastModified",
    "_locale",
    "_templateName",
}

ASSET_FIELD_MAP = {
    "au": "album_art",
    "tb": "thumbnail",
    "mu": "music_data",
    "ld": "lad_file",
}

JAM_PART_FIELD_MAP = {
    "siv": "vocals",
    "sib": "bass",
    "sid": "drums",
    "sig": "lead",
}

INTENSITY_SKIP_FIELDS = {"_type"}

CHUNK_SIZE = 250


@dataclass(frozen=True)
class TrackPage:
    epic_slug: str
    page: dict[str, Any]
    track: dict[str, Any]


def now_utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def chunked(items: list[dict[str, Any]], size: int = CHUNK_SIZE):
    for index in range(0, len(items), size):
        yield items[index : index + size]


def parse_iso_datetime(value: Any) -> str | None:
    if not isinstance(value, str) or not value.strip():
        return None
    return value


def parse_uuidish(value: Any) -> str | None:
    if not isinstance(value, str) or not value.strip():
        return None
    return value.strip()


def parse_qi(value: Any) -> dict[str, Any] | None:
    if not isinstance(value, str) or not value.strip():
        return None

    try:
        parsed = json.loads(value)
    except json.JSONDecodeError:
        return None

    return parsed if isinstance(parsed, dict) else None


def is_probably_url(value: str) -> bool:
    parsed = urlparse(value)
    return parsed.scheme in {"http", "https"} and bool(parsed.netloc)


def compute_camelot_code(musical_key: str | None, mode: str | None) -> str | None:
    if not musical_key or not mode:
        return None

    key = musical_key.strip()
    normalized_mode = mode.strip().lower()

    minor_map = {
        "Ab": "01A",
        "Eb": "02A",
        "Bb": "03A",
        "F": "04A",
        "C": "05A",
        "G": "06A",
        "D": "07A",
        "A": "08A",
        "E": "09A",
        "B": "10A",
        "Gb": "11A",
        "Db": "12A",
    }

    major_map = {
        "B": "01B",
        "Gb": "02B",
        "Db": "03B",
        "Ab": "04B",
        "Eb": "05B",
        "Bb": "06B",
        "F": "07B",
        "C": "08B",
        "G": "09B",
        "D": "10B",
        "A": "11B",
        "E": "12B",
    }

    if normalized_mode == "minor":
        return minor_map.get(key)

    if normalized_mode == "major":
        return major_map.get(key)

    return None


def fetch_epic_json() -> dict[str, Any]:
    response = requests.get(
        EPIC_SPARK_TRACKS_URL,
        headers={
            "User-Agent": "FNFest-GUI5-Batched-Importer/0.2",
            "Accept": "application/json",
        },
        timeout=30,
    )
    response.raise_for_status()
    return response.json()


def extract_track_pages(data: dict[str, Any]) -> list[TrackPage]:
    pages: list[TrackPage] = []

    for key, value in data.items():
        if key in ROOT_METADATA_FIELDS:
            continue

        if not isinstance(value, dict):
            continue

        track = value.get("track")
        if not isinstance(track, dict):
            continue

        pages.append(TrackPage(epic_slug=key, page=value, track=track))

    return pages


def load_supabase_client() -> Client:
    load_dotenv()

    supabase_url = os.getenv("SUPABASE_URL")
    service_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

    if not supabase_url:
        raise RuntimeError("Missing SUPABASE_URL in environment.")

    if not service_key:
        raise RuntimeError("Missing SUPABASE_SERVICE_ROLE_KEY in environment.")

    return create_client(supabase_url, service_key)


def insert_rows(client: Client, table: str, rows: list[dict[str, Any]], label: str) -> None:
    if not rows:
        print(f"  {label}: 0 rows")
        return

    inserted = 0

    for chunk in chunked(rows):
        client.table(table).insert(chunk).execute()
        inserted += len(chunk)

    print(f"  {label}: {inserted} rows")


def upsert_rows(
    client: Client,
    table: str,
    rows: list[dict[str, Any]],
    on_conflict: str,
    label: str,
) -> None:
    if not rows:
        print(f"  {label}: 0 rows")
        return

    upserted = 0

    for chunk in chunked(rows):
        client.table(table).upsert(chunk, on_conflict=on_conflict).execute()
        upserted += len(chunk)

    print(f"  {label}: {upserted} rows")


def create_import_batch(client: Client, data: dict[str, Any], track_count: int) -> int:
    response = (
        client.table("import_batches")
        .insert(
            {
                "source_name": "epic_spark_tracks",
                "source_url": EPIC_SPARK_TRACKS_URL,
                "source_title": data.get("_title"),
                "source_locale": data.get("_locale"),
                "source_template_name": data.get("_templateName"),
                "source_active_date": parse_iso_datetime(data.get("_activeDate")),
                "source_last_modified": parse_iso_datetime(data.get("lastModified")),
                "track_count": track_count,
                "notes": "Imported by batched scripts/import_epic_tracks.py",
            }
        )
        .execute()
    )

    if not response.data:
        raise RuntimeError("Failed to create import batch.")

    return int(response.data[0]["import_batch_id"])


def create_sync_run(client: Client, source_url: str) -> int:
    response = (
        client.table("sync_runs")
        .insert(
            {
                "source_name": "epic_spark_tracks",
                "source_url": source_url,
                "status": "running",
                "notes": "Started by local Python importer.",
            }
        )
        .execute()
    )

    if not response.data:
        raise RuntimeError("Failed to create sync run.")

    return int(response.data[0]["sync_run_id"])


def finish_sync_run(
    client: Client,
    sync_run_id: int,
    status: str,
    source_last_modified: str | None = None,
    source_track_count: int | None = None,
    import_batch_id: int | None = None,
    error_message: str | None = None,
    notes: str | None = None,
) -> None:
    client.table("sync_runs").update(
        {
            "finished_at": now_utc(),
            "status": status,
            "source_last_modified": source_last_modified,
            "source_track_count": source_track_count,
            "import_batch_id": import_batch_id,
            "error_message": error_message,
            "notes": notes,
        }
    ).eq("sync_run_id", sync_run_id).execute()


def get_latest_successful_import(client: Client) -> dict[str, Any] | None:
    response = (
        client.table("import_batches")
        .select("import_batch_id, source_last_modified, track_count, imported_at")
        .order("import_batch_id", desc=True)
        .limit(1)
        .execute()
    )

    if not response.data:
        return None

    return response.data[0]


def should_skip_import(
    latest_import: dict[str, Any] | None,
    source_last_modified: str | None,
    track_count: int,
) -> bool:
    if latest_import is None:
        return False

    latest_modified = latest_import.get("source_last_modified")
    latest_count = latest_import.get("track_count")

    return latest_modified == source_last_modified and latest_count == track_count


def clear_catalog_child_tables(client: Client) -> None:
    """
    Clears child catalog tables before reinserting current source relationships.

    This avoids per-track delete calls and prevents duplicate relationship rows
    on repeated imports.
    """
    tables_with_track_id = [
        "track_artists",
        "track_genres",
        "track_tags",
        "track_assets",
        "track_difficulties",
        "track_jam_parts",
        "track_audio_parts",
        "track_audio_metadata",
    ]

    print("Clearing catalog child tables...")

    for table in tables_with_track_id:
        client.table(table).delete().gte("track_id", 0).execute()
        print(f"  cleared {table}")


def fetch_track_id_map(client: Client) -> dict[str, int]:
    response = (
        client.table("tracks")
        .select("track_id, epic_slug")
        .execute()
    )

    return {
        row["epic_slug"]: int(row["track_id"])
        for row in response.data or []
    }


def fetch_artist_id_map(client: Client) -> dict[str, int]:
    response = client.table("artists").select("artist_id, name").execute()

    return {
        row["name"]: int(row["artist_id"])
        for row in response.data or []
    }


def fetch_genre_id_map(client: Client) -> dict[str, int]:
    response = client.table("genres").select("genre_id, genre_code").execute()

    return {
        row["genre_code"]: int(row["genre_id"])
        for row in response.data or []
    }


def fetch_tag_id_map(client: Client) -> dict[str, int]:
    response = client.table("tags").select("tag_id, tag_code").execute()

    return {
        row["tag_code"]: int(row["tag_id"])
        for row in response.data or []
    }


def split_artist_group(value: str | None) -> list[str]:
    if not value:
        return []

    parts = re.split(r"\s*,\s*|\s+&\s+", value)
    return [part.strip() for part in parts if part.strip()]


def normalize_artist_segments(artist_display: str | None) -> list[tuple[str, str]]:
    """
    Conservative artist parser.

    tracks.artist_display keeps Epic's exact string.
    artists/track_artists are only for better search/filtering.
    """
    if not artist_display:
        return []

    text = artist_display.strip()
    if not text:
        return []

    featured_pattern = re.compile(r"\s+(?:ft\.?|feat\.?|featuring)\s+", re.IGNORECASE)
    featured_parts = featured_pattern.split(text, maxsplit=1)

    primary_text = featured_parts[0].strip()
    featured_text = featured_parts[1].strip() if len(featured_parts) > 1 else None

    results: list[tuple[str, str]] = []

    for name in split_artist_group(primary_text):
        results.append((name, "primary"))

    for name in split_artist_group(featured_text):
        results.append((name, "featured"))

    if not results:
        results.append((text, "primary"))

    seen: set[tuple[str, str]] = set()
    deduped: list[tuple[str, str]] = []

    for name, role in results:
        key = (name.lower(), role)
        if key not in seen:
            seen.add(key)
            deduped.append((name, role))

    return deduped


def build_raw_track_rows(batch_id: int, track_pages: list[TrackPage]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []

    for item in track_pages:
        page = item.page

        rows.append(
            {
                "import_batch_id": batch_id,
                "epic_slug": item.epic_slug,
                "page_title": page.get("_title"),
                "page_no_index": page.get("_noIndex"),
                "page_active_date": parse_iso_datetime(page.get("_activeDate")),
                "page_last_modified": parse_iso_datetime(page.get("lastModified")),
                "page_locale": page.get("_locale"),
                "page_template_name": page.get("_templateName"),
                "raw_page_json": page,
                "raw_track_json": item.track,
            }
        )

    return rows


def build_track_rows(batch_id: int, track_pages: list[TrackPage]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    seen_at = now_utc()

    for item in track_pages:
        page = item.page
        track = item.track

        musical_key = track.get("mk")
        mode = track.get("mm")

        rows.append(
            {
                "epic_slug": item.epic_slug,
                "song_slug": track.get("sn"),
                "song_uuid": parse_uuidish(track.get("su")),
                "sparks_song_id": track.get("ti"),
                "title": track.get("tt") or item.epic_slug,
                "artist_display": track.get("an"),
                "album_title": track.get("ab"),
                "release_year": track.get("ry"),
                "duration_seconds": track.get("dn"),
                "bpm": track.get("mt"),
                "musical_key": musical_key,
                "mode": mode,
                "camelot_code": compute_camelot_code(musical_key, mode),
                "rating_code": track.get("ar"),
                "isrc": track.get("isrc"),
                "jam_code": track.get("jc"),
                "mmo": track.get("mmo"),
                "ci": track.get("ci"),
                "ag": track.get("ag"),
                "sm": track.get("sm"),
                "no_index": page.get("_noIndex"),
                "active_date": parse_iso_datetime(page.get("_activeDate")),
                "new_until": parse_iso_datetime(track.get("nu")),
                "last_modified": parse_iso_datetime(page.get("lastModified")),
                "locale": page.get("_locale"),
                "template_name": page.get("_templateName"),
                "last_seen_at": seen_at,
                "last_import_batch_id": batch_id,
            }
        )

    return rows


def collect_lookup_values(track_pages: list[TrackPage]) -> tuple[set[str], set[str], set[str]]:
    artist_names: set[str] = set()
    genre_codes: set[str] = set()
    tag_codes: set[str] = set()

    for item in track_pages:
        track = item.track

        for artist_name, _role in normalize_artist_segments(track.get("an")):
            artist_names.add(artist_name)

        for genre_code in track.get("ge") or []:
            genre_codes.add(str(genre_code))

        for tag_code in track.get("gt") or []:
            tag_codes.add(str(tag_code))

    return artist_names, genre_codes, tag_codes


def build_lookup_rows(values: set[str], code_field: str, label_field: str) -> list[dict[str, Any]]:
    return [
        {
            code_field: value,
            label_field: value,
        }
        for value in sorted(values)
    ]


def build_artist_rows(values: set[str]) -> list[dict[str, Any]]:
    return [{"name": value} for value in sorted(values)]


def build_child_rows(
    track_pages: list[TrackPage],
    track_id_map: dict[str, int],
    artist_id_map: dict[str, int],
    genre_id_map: dict[str, int],
    tag_id_map: dict[str, int],
) -> dict[str, list[dict[str, Any]]]:
    rows: dict[str, list[dict[str, Any]]] = {
        "track_artists": [],
        "track_genres": [],
        "track_tags": [],
        "track_assets": [],
        "track_difficulties": [],
        "track_jam_parts": [],
        "track_audio_metadata": [],
        "track_audio_parts": [],
    }

    for item in track_pages:
        track_id = track_id_map.get(item.epic_slug)
        if track_id is None:
            raise RuntimeError(f"Missing track_id for epic_slug={item.epic_slug}")

        track = item.track

        for index, (artist_name, role) in enumerate(normalize_artist_segments(track.get("an")), start=1):
            artist_id = artist_id_map.get(artist_name)
            if artist_id is None:
                continue

            rows["track_artists"].append(
                {
                    "track_id": track_id,
                    "artist_id": artist_id,
                    "artist_order": index,
                    "artist_role": role,
                    "source_text": artist_name,
                }
            )

        for genre_code in track.get("ge") or []:
            genre_id = genre_id_map.get(str(genre_code))
            if genre_id is not None:
                rows["track_genres"].append(
                    {
                        "track_id": track_id,
                        "genre_id": genre_id,
                    }
                )

        for tag_code in track.get("gt") or []:
            tag_id = tag_id_map.get(str(tag_code))
            if tag_id is not None:
                rows["track_tags"].append(
                    {
                        "track_id": track_id,
                        "tag_id": tag_id,
                    }
                )

        for source_field, asset_type in ASSET_FIELD_MAP.items():
            url = track.get(source_field)
            if isinstance(url, str) and is_probably_url(url):
                rows["track_assets"].append(
                    {
                        "track_id": track_id,
                        "asset_type": asset_type,
                        "url": url,
                    }
                )

        intensities = track.get("in")
        if isinstance(intensities, dict):
            for part_code, value in intensities.items():
                if part_code in INTENSITY_SKIP_FIELDS:
                    continue

                if isinstance(value, int):
                    rows["track_difficulties"].append(
                        {
                            "track_id": track_id,
                            "part_code": part_code,
                            "difficulty_value": value,
                        }
                    )

        for source_field, _slot_name in JAM_PART_FIELD_MAP.items():
            instrument_name = track.get(source_field)
            if isinstance(instrument_name, str) and instrument_name.strip():
                rows["track_jam_parts"].append(
                    {
                        "track_id": track_id,
                        "slot_code": source_field,
                        "instrument_name": instrument_name,
                    }
                )

        qi = parse_qi(track.get("qi"))
        if qi:
            preview = qi.get("preview") if isinstance(qi.get("preview"), dict) else {}

            rows["track_audio_metadata"].append(
                {
                    "track_id": track_id,
                    "qi_sid": parse_uuidish(qi.get("sid")),
                    "qi_pid": parse_uuidish(qi.get("pid")),
                    "stereo_id": parse_uuidish(qi.get("stereoId")),
                    "instrumental_id": parse_uuidish(qi.get("instrumentalId")),
                    "qi_title": qi.get("title"),
                    "preview_start_time": preview.get("starttime"),
                    "raw_qi": qi,
                }
            )

            for audio_part in qi.get("tracks") or []:
                if not isinstance(audio_part, dict):
                    continue

                part_code = audio_part.get("part")
                if not isinstance(part_code, str) or not part_code.strip():
                    continue

                rows["track_audio_parts"].append(
                    {
                        "track_id": track_id,
                        "audio_part_code": part_code,
                        "channels": audio_part.get("channels") or [],
                        "volumes": audio_part.get("vols") or [],
                    }
                )

    return rows


def main() -> int:
    print("Loading Supabase client...")
    client = load_supabase_client()

    sync_run_id: int | None = None

    try:
        print("Creating sync run...")
        sync_run_id = create_sync_run(client, EPIC_SPARK_TRACKS_URL)
        print(f"Sync run ID: {sync_run_id}")

        print("Fetching Epic spark-tracks JSON...")
        data = fetch_epic_json()

        track_pages = extract_track_pages(data)
        track_count = len(track_pages)
        source_last_modified = parse_iso_datetime(data.get("lastModified"))

        print(f"Found {track_count} track pages.")
        print(f"Source lastModified: {source_last_modified}")

        latest_import = get_latest_successful_import(client)

        if should_skip_import(latest_import, source_last_modified, track_count):
            print("No source changes detected. Skipping import.")

            finish_sync_run(
                client=client,
                sync_run_id=sync_run_id,
                status="skipped",
                source_last_modified=source_last_modified,
                source_track_count=track_count,
                import_batch_id=latest_import.get("import_batch_id") if latest_import else None,
                notes="Skipped because source lastModified and track count matched latest import.",
            )

            return 0

        print("Changes detected or no previous import exists.")
        print("Creating import batch...")
        batch_id = create_import_batch(client, data, track_count)
        print(f"Import batch ID: {batch_id}")

        print("Building rows in memory...")
        raw_track_rows = build_raw_track_rows(batch_id, track_pages)
        track_rows = build_track_rows(batch_id, track_pages)
        artist_names, genre_codes, tag_codes = collect_lookup_values(track_pages)

        artist_rows = build_artist_rows(artist_names)
        genre_rows = build_lookup_rows(genre_codes, "genre_code", "genre_label")
        tag_rows = build_lookup_rows(tag_codes, "tag_code", "tag_label")

        print("Clearing existing child catalog rows...")
        clear_catalog_child_tables(client)

        print("Writing raw/current catalog rows...")
        insert_rows(client, "raw_tracks", raw_track_rows, "raw_tracks")
        upsert_rows(client, "tracks", track_rows, "epic_slug", "tracks")
        upsert_rows(client, "artists", artist_rows, "name", "artists")
        upsert_rows(client, "genres", genre_rows, "genre_code", "genres")
        upsert_rows(client, "tags", tag_rows, "tag_code", "tags")

        print("Fetching ID maps...")
        track_id_map = fetch_track_id_map(client)
        artist_id_map = fetch_artist_id_map(client)
        genre_id_map = fetch_genre_id_map(client)
        tag_id_map = fetch_tag_id_map(client)

        print("Building child relationship rows...")
        child_rows = build_child_rows(
            track_pages=track_pages,
            track_id_map=track_id_map,
            artist_id_map=artist_id_map,
            genre_id_map=genre_id_map,
            tag_id_map=tag_id_map,
        )

        print("Writing child relationship rows...")
        insert_rows(client, "track_artists", child_rows["track_artists"], "track_artists")
        insert_rows(client, "track_genres", child_rows["track_genres"], "track_genres")
        insert_rows(client, "track_tags", child_rows["track_tags"], "track_tags")
        insert_rows(client, "track_assets", child_rows["track_assets"], "track_assets")
        insert_rows(client, "track_difficulties", child_rows["track_difficulties"], "track_difficulties")
        insert_rows(client, "track_jam_parts", child_rows["track_jam_parts"], "track_jam_parts")
        insert_rows(client, "track_audio_metadata", child_rows["track_audio_metadata"], "track_audio_metadata")
        insert_rows(client, "track_audio_parts", child_rows["track_audio_parts"], "track_audio_parts")

        finish_sync_run(
            client=client,
            sync_run_id=sync_run_id,
            status="success",
            source_last_modified=source_last_modified,
            source_track_count=track_count,
            import_batch_id=batch_id,
            notes="Import completed successfully.",
        )

        print("Import complete.")
        print(f"Tracks processed: {track_count}")
        return 0

    except Exception as exc:
        if sync_run_id is not None:
            try:
                finish_sync_run(
                    client=client,
                    sync_run_id=sync_run_id,
                    status="failed",
                    error_message=str(exc),
                    notes="Import failed.",
                )
            except Exception:
                pass

        raise

if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise SystemExit(1)