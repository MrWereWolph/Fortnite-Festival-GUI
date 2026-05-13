#!/usr/bin/env python3
"""
FNFest GUI5 - Epic Spark Tracks Inspector

Purpose:
    Fetch Epic's spark-tracks JSON and inspect the structure before writing
    the real Supabase importer.

This script reports:
    - root/page metadata
    - number of track entries
    - all observed track fields
    - how often each field appears
    - all observed intensity/difficulty fields
    - all observed qi fields
    - example values for each field
    - possible schema warnings

This does NOT write to Supabase.
"""

from __future__ import annotations

import json
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


EPIC_SPARK_TRACKS_URL = (
    "https://fortnitecontent-website-prod07.ol.epicgames.com/"
    "content/api/pages/fortnite-game/spark-tracks"
)

PROJECT_ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = PROJECT_ROOT / "data" / "reports"
OUTPUT_JSON = OUTPUT_DIR / "epic_field_report.json"
OUTPUT_MD = OUTPUT_DIR / "epic_field_report.md"


ROOT_METADATA_FIELDS = {
    "_title",
    "_noIndex",
    "_activeDate",
    "lastModified",
    "_locale",
    "_templateName",
}


def fetch_json(url: str) -> dict[str, Any]:
    request = Request(
        url,
        headers={
            "User-Agent": "FNFest-GUI5-Inspector/0.1",
            "Accept": "application/json",
        },
    )

    try:
        with urlopen(request, timeout=30) as response:
            raw = response.read().decode("utf-8")
            return json.loads(raw)
    except HTTPError as exc:
        raise RuntimeError(f"HTTP error while fetching Epic data: {exc.code}") from exc
    except URLError as exc:
        raise RuntimeError(f"Network error while fetching Epic data: {exc}") from exc
    except json.JSONDecodeError as exc:
        raise RuntimeError("Epic response was not valid JSON.") from exc


def short_example(value: Any, max_length: int = 120) -> str:
    if isinstance(value, str):
        text = value
    else:
        text = json.dumps(value, ensure_ascii=False, sort_keys=True)

    text = text.replace("\n", " ").replace("\r", " ")

    if len(text) > max_length:
        return text[: max_length - 3] + "..."

    return text


def add_example(examples: dict[str, list[str]], key: str, value: Any, limit: int = 5) -> None:
    example = short_example(value)

    if example not in examples[key] and len(examples[key]) < limit:
        examples[key].append(example)


def safe_parse_qi(value: Any) -> dict[str, Any] | None:
    if not isinstance(value, str) or not value.strip():
        return None

    try:
        parsed = json.loads(value)
    except json.JSONDecodeError:
        return None

    if isinstance(parsed, dict):
        return parsed

    return None


def inspect(data: dict[str, Any]) -> dict[str, Any]:
    root_metadata = {
        key: data.get(key)
        for key in ROOT_METADATA_FIELDS
        if key in data
    }

    track_pages: list[tuple[str, dict[str, Any]]] = []

    for key, value in data.items():
        if key in ROOT_METADATA_FIELDS:
            continue

        if isinstance(value, dict) and isinstance(value.get("track"), dict):
            track_pages.append((key, value))

    track_field_counts: Counter[str] = Counter()
    page_field_counts: Counter[str] = Counter()
    intensity_field_counts: Counter[str] = Counter()
    qi_field_counts: Counter[str] = Counter()
    qi_track_part_counts: Counter[str] = Counter()

    track_field_examples: dict[str, list[str]] = defaultdict(list)
    page_field_examples: dict[str, list[str]] = defaultdict(list)
    intensity_examples: dict[str, list[str]] = defaultdict(list)
    qi_examples: dict[str, list[str]] = defaultdict(list)
    genre_counts: Counter[str] = Counter()
    tag_counts: Counter[str] = Counter()
    rating_counts: Counter[str] = Counter()
    mode_counts: Counter[str] = Counter()
    key_counts: Counter[str] = Counter()

    malformed_qi_count = 0
    missing_qi_count = 0
    tracks_with_isrc = 0
    tracks_without_isrc = 0

    duplicate_isrcs: dict[str, list[str]] = defaultdict(list)
    duplicate_song_uuids: dict[str, list[str]] = defaultdict(list)
    duplicate_jam_codes: dict[str, list[str]] = defaultdict(list)

    for epic_slug, page in track_pages:
        for page_field, page_value in page.items():
            if page_field == "track":
                continue

            page_field_counts[page_field] += 1
            add_example(page_field_examples, page_field, page_value)

        track = page["track"]

        for field, value in track.items():
            track_field_counts[field] += 1
            add_example(track_field_examples, field, value)

        isrc = track.get("isrc")
        if isrc:
            tracks_with_isrc += 1
            duplicate_isrcs[str(isrc)].append(epic_slug)
        else:
            tracks_without_isrc += 1

        song_uuid = track.get("su")
        if song_uuid:
            duplicate_song_uuids[str(song_uuid)].append(epic_slug)

        jam_code = track.get("jc")
        if jam_code:
            duplicate_jam_codes[str(jam_code)].append(epic_slug)

        for genre in track.get("ge") or []:
            genre_counts[str(genre)] += 1

        for tag in track.get("gt") or []:
            tag_counts[str(tag)] += 1

        if track.get("ar"):
            rating_counts[str(track["ar"])] += 1

        if track.get("mm"):
            mode_counts[str(track["mm"])] += 1

        if track.get("mk"):
            key_counts[str(track["mk"])] += 1

        intensities = track.get("in")
        if isinstance(intensities, dict):
            for part_code, difficulty in intensities.items():
                intensity_field_counts[part_code] += 1
                add_example(intensity_examples, part_code, difficulty)

        qi_raw = track.get("qi")
        if qi_raw is None:
            missing_qi_count += 1
        else:
            qi = safe_parse_qi(qi_raw)
            if qi is None:
                malformed_qi_count += 1
            else:
                for qi_field, qi_value in qi.items():
                    qi_field_counts[qi_field] += 1
                    add_example(qi_examples, qi_field, qi_value)

                for part in qi.get("tracks") or []:
                    if isinstance(part, dict) and part.get("part"):
                        qi_track_part_counts[str(part["part"])] += 1

    duplicate_isrcs = {
        key: slugs
        for key, slugs in duplicate_isrcs.items()
        if len(slugs) > 1
    }

    duplicate_song_uuids = {
        key: slugs
        for key, slugs in duplicate_song_uuids.items()
        if len(slugs) > 1
    }

    duplicate_jam_codes = {
        key: slugs
        for key, slugs in duplicate_jam_codes.items()
        if len(slugs) > 1
    }

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source_url": EPIC_SPARK_TRACKS_URL,
        "root_metadata": root_metadata,
        "track_count": len(track_pages),
        "page_field_counts": dict(sorted(page_field_counts.items())),
        "page_field_examples": dict(sorted(page_field_examples.items())),
        "track_field_counts": dict(sorted(track_field_counts.items())),
        "track_field_examples": dict(sorted(track_field_examples.items())),
        "intensity_field_counts": dict(sorted(intensity_field_counts.items())),
        "intensity_examples": dict(sorted(intensity_examples.items())),
        "qi_field_counts": dict(sorted(qi_field_counts.items())),
        "qi_field_examples": dict(sorted(qi_examples.items())),
        "qi_track_part_counts": dict(sorted(qi_track_part_counts.items())),
        "genre_counts": dict(genre_counts.most_common()),
        "tag_counts": dict(tag_counts.most_common()),
        "rating_counts": dict(rating_counts.most_common()),
        "mode_counts": dict(mode_counts.most_common()),
        "key_counts": dict(key_counts.most_common()),
        "tracks_with_isrc": tracks_with_isrc,
        "tracks_without_isrc": tracks_without_isrc,
        "missing_qi_count": missing_qi_count,
        "malformed_qi_count": malformed_qi_count,
        "duplicate_isrcs": duplicate_isrcs,
        "duplicate_song_uuids": duplicate_song_uuids,
        "duplicate_jam_codes": duplicate_jam_codes,
    }


def markdown_counter_section(title: str, values: dict[str, Any]) -> str:
    lines = [f"## {title}", ""]

    if not values:
        lines.append("_No values found._")
        lines.append("")
        return "\n".join(lines)

    lines.append("| Value | Count |")
    lines.append("|---|---:|")

    for key, count in values.items():
        lines.append(f"| `{key}` | {count} |")

    lines.append("")
    return "\n".join(lines)


def markdown_field_section(
    title: str,
    counts: dict[str, int],
    examples: dict[str, list[str]],
    track_count: int,
) -> str:
    lines = [f"## {title}", ""]

    lines.append("| Field | Count | Missing | Example Values |")
    lines.append("|---|---:|---:|---|")

    for field, count in counts.items():
        missing = track_count - count
        example_text = "<br>".join(f"`{example}`" for example in examples.get(field, []))
        lines.append(f"| `{field}` | {count} | {missing} | {example_text} |")

    lines.append("")
    return "\n".join(lines)


def write_markdown_report(report: dict[str, Any], path: Path) -> None:
    track_count = int(report["track_count"])

    lines = [
        "# FNFest GUI5 Epic Field Report",
        "",
        f"Generated at: `{report['generated_at']}`",
        "",
        f"Source URL: `{report['source_url']}`",
        "",
        f"Track count: **{track_count}**",
        "",
        "## Root Metadata",
        "",
        "| Field | Value |",
        "|---|---|",
    ]

    for key, value in report["root_metadata"].items():
        lines.append(f"| `{key}` | `{short_example(value)}` |")

    lines.append("")

    lines.append(
        markdown_field_section(
            "Page Fields",
            report["page_field_counts"],
            report["page_field_examples"],
            track_count,
        )
    )

    lines.append(
        markdown_field_section(
            "Track Fields",
            report["track_field_counts"],
            report["track_field_examples"],
            track_count,
        )
    )

    lines.append(
        markdown_field_section(
            "Intensity Fields",
            report["intensity_field_counts"],
            report["intensity_examples"],
            track_count,
        )
    )

    lines.append(
        markdown_field_section(
            "QI Fields",
            report["qi_field_counts"],
            report["qi_field_examples"],
            track_count,
        )
    )

    lines.append(markdown_counter_section("QI Track Part Codes", report["qi_track_part_counts"]))
    lines.append(markdown_counter_section("Genres", report["genre_counts"]))
    lines.append(markdown_counter_section("Gameplay Tags", report["tag_counts"]))
    lines.append(markdown_counter_section("Ratings", report["rating_counts"]))
    lines.append(markdown_counter_section("Modes", report["mode_counts"]))
    lines.append(markdown_counter_section("Keys", report["key_counts"]))

    lines.extend(
        [
            "## Warnings / Data Quality",
            "",
            f"- Tracks with ISRC: **{report['tracks_with_isrc']}**",
            f"- Tracks without ISRC: **{report['tracks_without_isrc']}**",
            f"- Tracks missing QI: **{report['missing_qi_count']}**",
            f"- Tracks with malformed QI: **{report['malformed_qi_count']}**",
            f"- Duplicate ISRC values: **{len(report['duplicate_isrcs'])}**",
            f"- Duplicate song UUID values: **{len(report['duplicate_song_uuids'])}**",
            f"- Duplicate jam codes: **{len(report['duplicate_jam_codes'])}**",
            "",
        ]
    )

    if report["duplicate_isrcs"]:
        lines.append("### Duplicate ISRCs")
        lines.append("")
        lines.append("| ISRC | Epic Slugs |")
        lines.append("|---|---|")
        for isrc, slugs in report["duplicate_isrcs"].items():
            lines.append(f"| `{isrc}` | `{', '.join(slugs)}` |")
        lines.append("")

    path.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    print("Fetching Epic spark-tracks JSON...")
    data = fetch_json(EPIC_SPARK_TRACKS_URL)

    print("Inspecting fields...")
    report = inspect(data)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    OUTPUT_JSON.write_text(
        json.dumps(report, indent=2, ensure_ascii=False, sort_keys=True),
        encoding="utf-8",
    )

    write_markdown_report(report, OUTPUT_MD)

    print()
    print("Inspection complete.")
    print(f"Track count: {report['track_count']}")
    print(f"JSON report: {OUTPUT_JSON}")
    print(f"Markdown report: {OUTPUT_MD}")
    print()

    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except RuntimeError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise SystemExit(1)