#!/usr/bin/env python3
"""
FNFest GUI5 - Epic Spark Tracks Supabase Importer

Purpose:
    Fetch Epic's spark-tracks JSON, preserve raw track JSON, and upsert
    normalized Fortnite Festival catalog data into Supabase/Postgres.

Requirements:
    pip install -r requirements.txt

Required .env values:
    SUPABASE_URL=
    SUPABASE_SERVICE_ROLE_KEY=

Important:
    The service role key must never be exposed to browser/frontend code.
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


@dataclass(frozen=True)
class TrackPage:
    epic_slug: str
    page: dict[str, Any]
    track: dict[str, Any]


def parse_iso_datetime(value: Any) -> str | None:
    if not isinstance(value, str) or not value.strip():
        return None

    # Postgres accepts ISO timestamps with Z, so preserve the string.
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

    if isinstance(parsed, dict):
        return parsed

    return None


def compute_camelot_code(musical_key: str | None, mode: str | None) -> str | None:
    """
    Convert key/mode to Camelot notation.

    Camelot wheel:
        Minor:
            Ab 01A, Eb 02A, Bb 03A, F 04A, C 05A, G 06A,
            D 07A, A 08A, E 09A, B 10A, Gb 11A, Db 12A

        Major:
            B 01B, Gb 02B, Db 03B, Ab 04B, Eb 05B, Bb 06B,
            F 07B, C 08B, G 09B, D 10B, A 11B, E 12B
    """
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
            "User-Agent": "FNFest-GUI5-Importer/0.1",
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


def upsert_one(
    client: Client,
    table: str,
    row: dict[str, Any],
    on_conflict: str,
) -> dict[str, Any]:
    response = (
        client.table(table)
        .upsert(row, on_conflict=on_conflict)
        .execute()
    )

    if not response.data:
        raise RuntimeError(f"Upsert into {table} returned no data.")

    return response.data[0]


def insert_rows(
    client: Client,
    table: str,
    rows: list[dict[str, Any]],
) -> None:
    if not rows:
        return

    client.table(table).insert(rows).execute()


def delete_track_children(client: Client, track_id: int) -> None:
    """
    Clear per-track child tables before re-inserting current source values.
    This keeps relationships accurate when Epic removes a tag/genre/asset/etc.
    """
    child_tables = [
        "track_artists",
        "track_genres",
        "track_tags",
        "track_assets",
        "track_difficulties",
        "track_jam_parts",
        "track_audio_parts",
        "track_audio_metadata",
    ]

    for table in child_tables:
        client.table(table).delete().eq("track_id", track_id).execute()


def normalize_artist_segments(artist_display: str | None) -> list[tuple[str, str]]:
    """
    Conservative artist parser.

    Keeps tracks.artist_display as the official display string.
    This parser only creates helpful search rows.

    Examples:
        "Billie Eilish" -> [("Billie Eilish", "primary")]
        "mgk ft. WILLOW" -> [("mgk", "primary"), ("WILLOW", "featured")]
        "Elton John & Britney Spears" -> both collaborator-ish
    """
    if not artist_display:
        return []

    text = artist_display.strip()
    if not text:
        return []

    # Split common featured markers first.
    featured_pattern = re.compile(r"\s+(?:ft\.?|feat\.?|featuring)\s+", re.IGNORECASE)
    featured_parts = featured_pattern.split(text, maxsplit=1)

    results: list[tuple[str, str]] = []

    primary_text = featured_parts[0].strip()
    featured_text = featured_parts[1].strip() if len(featured_parts) > 1 else None

    primary_names = split_artist_group(primary_text)
    featured_names = split_artist_group(featured_text) if featured_text else []

    for name in primary_names:
        results.append((name, "primary"))

    for name in featured_names:
        results.append((name, "featured"))

    if not results:
        results.append((text, "primary"))

    # De-duplicate while preserving order.
    seen: set[tuple[str, str]] = set()
    deduped: list[tuple[str, str]] = []

    for name, role in results:
        key = (name.lower(), role)
        if key not in seen:
            seen.add(key)
            deduped.append((name, role))

    return deduped


def split_artist_group(value: str | None) -> list[str]:
    if not value:
        return []

    # Split on comma and ampersand when used as separators.
    # Do not split on "The" or plus signs; keep this conservative.
    parts = re.split(r"\s*,\s*|\s+&\s+", value)

    return [part.strip() for part in parts if part.strip()]


def upsert_artist(client: Client, name: str) -> int:
    row = upsert_one(
        client,
        "artists",
        {"name": name},
        on_conflict="name",
    )
    return int(row["artist_id"])


def upsert_genre(client: Client, genre_code: str) -> int:
    row = upsert_one(
        client,
        "genres",
        {
            "genre_code": genre_code,
            "genre_label": genre_code,
        },
        on_conflict="genre_code",
    )
    return int(row["genre_id"])


def upsert_tag(client: Client, tag_code: str) -> int:
    row = upsert_one(
        client,
        "tags",
        {
            "tag_code": tag_code,
            "tag_label": tag_code,
        },
        on_conflict="tag_code",
    )
    return int(row["tag_id"])


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
                "notes": "Imported by scripts/import_epic_tracks.py",
            }
        )
        .execute()
    )

    if not response.data:
        raise RuntimeError("Failed to create import batch.")

    return int(response.data[0]["import_batch_id"])


def import_track(client: Client, batch_id: int, item: TrackPage) -> None:
    page = item.page
    track = item.track

    # 1. Raw preservation
    raw_track_json = track

    client.table("raw_tracks").upsert(
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
            "raw_track_json": raw_track_json,
        },
        on_conflict="import_batch_id,epic_slug",
    ).execute()

    # 2. Main track row
    musical_key = track.get("mk")
    mode = track.get("mm")

    track_row = {
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
        "last_seen_at": datetime.now(timezone.utc).isoformat(),
        "last_import_batch_id": batch_id,
    }

    saved_track = upsert_one(
        client,
        "tracks",
        track_row,
        on_conflict="epic_slug",
    )
    track_id = int(saved_track["track_id"])

    # 3. Clear existing children for this track.
    delete_track_children(client, track_id)

    # 4. Artists
    artist_rows: list[dict[str, Any]] = []
    artist_segments = normalize_artist_segments(track.get("an"))

    for index, (artist_name, role) in enumerate(artist_segments, start=1):
        artist_id = upsert_artist(client, artist_name)
        artist_rows.append(
            {
                "track_id": track_id,
                "artist_id": artist_id,
                "artist_order": index,
                "artist_role": role,
                "source_text": artist_name,
            }
        )

    insert_rows(client, "track_artists", artist_rows)

    # 5. Genres
    genre_rows: list[dict[str, Any]] = []
    for genre_code in track.get("ge") or []:
        genre_id = upsert_genre(client, str(genre_code))
        genre_rows.append({"track_id": track_id, "genre_id": genre_id})

    insert_rows(client, "track_genres", genre_rows)

    # 6. Tags
    tag_rows: list[dict[str, Any]] = []
    for tag_code in track.get("gt") or []:
        tag_id = upsert_tag(client, str(tag_code))
        tag_rows.append({"track_id": track_id, "tag_id": tag_id})

    insert_rows(client, "track_tags", tag_rows)

    # 7. Assets
    asset_rows: list[dict[str, Any]] = []
    for source_field, asset_type in ASSET_FIELD_MAP.items():
        url = track.get(source_field)
        if isinstance(url, str) and is_probably_url(url):
            asset_rows.append(
                {
                    "track_id": track_id,
                    "asset_type": asset_type,
                    "url": url,
                }
            )

    insert_rows(client, "track_assets", asset_rows)

    # 8. Difficulties / intensities
    difficulty_rows: list[dict[str, Any]] = []
    intensities = track.get("in")

    if isinstance(intensities, dict):
        for part_code, value in intensities.items():
            if part_code in INTENSITY_SKIP_FIELDS:
                continue

            if isinstance(value, int):
                difficulty_rows.append(
                    {
                        "track_id": track_id,
                        "part_code": part_code,
                        "difficulty_value": value,
                    }
                )

    insert_rows(client, "track_difficulties", difficulty_rows)

    # 9. Jam parts
    jam_part_rows: list[dict[str, Any]] = []
    for source_field, slot_name in JAM_PART_FIELD_MAP.items():
        instrument_name = track.get(source_field)

        if isinstance(instrument_name, str) and instrument_name.strip():
            jam_part_rows.append(
                {
                    "track_id": track_id,
                    "slot_code": source_field,
                    "instrument_name": instrument_name,
                }
            )

    insert_rows(client, "track_jam_parts", jam_part_rows)

    # 10. QI/audio metadata
    qi = parse_qi(track.get("qi"))

    if qi:
        preview = qi.get("preview") if isinstance(qi.get("preview"), dict) else {}
        preview_start_time = preview.get("starttime")

        client.table("track_audio_metadata").insert(
            {
                "track_id": track_id,
                "qi_sid": parse_uuidish(qi.get("sid")),
                "qi_pid": parse_uuidish(qi.get("pid")),
                "stereo_id": parse_uuidish(qi.get("stereoId")),
                "instrumental_id": parse_uuidish(qi.get("instrumentalId")),
                "qi_title": qi.get("title"),
                "preview_start_time": preview_start_time,
                "raw_qi": qi,
            }
        ).execute()

        audio_part_rows: list[dict[str, Any]] = []

        for audio_part in qi.get("tracks") or []:
            if not isinstance(audio_part, dict):
                continue

            part_code = audio_part.get("part")
            if not isinstance(part_code, str) or not part_code.strip():
                continue

            audio_part_rows.append(
                {
                    "track_id": track_id,
                    "audio_part_code": part_code,
                    "channels": audio_part.get("channels") or [],
                    "volumes": audio_part.get("vols") or [],
                }
            )

        insert_rows(client, "track_audio_parts", audio_part_rows)


def is_probably_url(value: str) -> bool:
    parsed = urlparse(value)
    return parsed.scheme in {"http", "https"} and bool(parsed.netloc)


def load_supabase_client() -> Client:
    load_dotenv()

    supabase_url = os.getenv("SUPABASE_URL")
    service_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

    if not supabase_url:
        raise RuntimeError("Missing SUPABASE_URL in environment.")

    if not service_key:
        raise RuntimeError("Missing SUPABASE_SERVICE_ROLE_KEY in environment.")

    return create_client(supabase_url, service_key)


def main() -> int:
    print("Loading Supabase client...")
    client = load_supabase_client()

    print("Fetching Epic spark-tracks JSON...")
    data = fetch_epic_json()

    track_pages = extract_track_pages(data)
    print(f"Found {len(track_pages)} track pages.")

    print("Creating import batch...")
    batch_id = create_import_batch(client, data, len(track_pages))
    print(f"Import batch ID: {batch_id}")

    imported = 0

    for item in track_pages:
        import_track(client, batch_id, item)
        imported += 1

        if imported % 25 == 0:
            print(f"Imported {imported}/{len(track_pages)} tracks...")

    print(f"Imported {imported}/{len(track_pages)} tracks.")
    print("Done.")

    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise SystemExit(1)