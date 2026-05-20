import { useEffect, useMemo, useState } from "react";
import { supabase } from "../lib/supabaseClient";
import { loadOwnedTrackIds, toggleOwnedTrackId } from "../lib/ownedTracks";
import JamTrackCard from "../components/JamTrackCard";

const JAM_RESULT_LIMIT = 48;
const SEARCH_DEBOUNCE_MS = 250;

export default function JamSearchPage() {
  const [tracks, setTracks] = useState([]);
  const [search, setSearch] = useState("");
  const [ownedOnly, setOwnedOnly] = useState(false);
  const [ownedIds, setOwnedIds] = useState(() => loadOwnedTrackIds());
  const [loading, setLoading] = useState(false);
  const [errorMessage, setErrorMessage] = useState("");

  async function loadTracks(searchText = "") {
    setLoading(true);
    setErrorMessage("");

    let query = supabase
      .from("v_tracks_search")
      .select(
        "track_id, epic_slug, title, artist_display, album_art_url, bpm, musical_key, mode, camelot_code, duration_seconds, rating_code"
      )
      .order("title", { ascending: true })
      .limit(JAM_RESULT_LIMIT);

    if (searchText.trim()) {
      const value = `%${searchText.trim()}%`;
      query = query.or(
        `title.ilike.${value},artist_display.ilike.${value},epic_slug.ilike.${value}`
      );
    }

    const { data, error } = await query;

    if (error) {
      setErrorMessage(error.message);
      setTracks([]);
    } else {
      setTracks(data ?? []);
    }

    setLoading(false);
  }

  useEffect(() => {
    const timeout = setTimeout(() => {
      loadTracks(search);
    }, SEARCH_DEBOUNCE_MS);

    return () => clearTimeout(timeout);
  }, [search]);

  const visibleTracks = useMemo(() => {
    if (!ownedOnly) return tracks;
    return tracks.filter((track) => ownedIds.has(Number(track.track_id)));
  }, [tracks, ownedOnly, ownedIds]);

  function handleSubmit(event) {
    event.preventDefault();
    loadTracks(search);
  }

  function handleToggleOwned(trackId) {
    const next = toggleOwnedTrackId(trackId);
    setOwnedIds(new Set(next));
  }

  return (
    <section className="page">
      <div className="tab-header">
        <div>
          <p className="eyebrow">Jam Search</p>
          <h1>Mix-focused track search</h1>
          <p className="muted">
            Search by title, artist, or slug. BPM, key, mode, and Camelot filters come next.
          </p>
        </div>

        <label className="toggle-row">
          <input
            type="checkbox"
            checked={ownedOnly}
            onChange={(event) => setOwnedOnly(event.target.checked)}
          />
          <span>Owned only</span>
        </label>
      </div>

      <form onSubmit={handleSubmit} className="panel search-row">
        <input
          className="input"
          value={search}
          onChange={(event) => setSearch(event.target.value)}
          placeholder="Search title, artist, or slug..."
        />
        <button className="btn primary" type="submit">
          Search
        </button>
      </form>

      <div className="result-bar">
        {loading ? "Loading tracks..." : `${visibleTracks.length} shown / ${tracks.length} loaded`}
        {tracks.length >= JAM_RESULT_LIMIT && (
          <span className="muted">Showing first {JAM_RESULT_LIMIT} matches</span>
        )}
        {errorMessage && <span className="error">Error: {errorMessage}</span>}
      </div>

      <section className="track-grid">
        {visibleTracks.map((track) => (
          <JamTrackCard
            key={track.track_id}
            track={track}
            owned={ownedIds.has(Number(track.track_id))}
            onToggleOwned={handleToggleOwned}
          />
        ))}
      </section>
    </section>
  );
}