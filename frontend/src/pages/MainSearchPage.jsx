import { useEffect, useMemo, useState } from "react";
import { supabase } from "../lib/supabaseClient";
import { loadOwnedTrackIds, toggleOwnedTrackId } from "../lib/ownedTracks";
import TrackCard from "../components/TrackCard";

const MAIN_RESULT_LIMIT = 96;
const SEARCH_DEBOUNCE_MS = 300;

const INSTRUMENTS = [
  { value: "band", label: "Band" },
  { value: "vocals", label: "Vocals" },
  { value: "guitar", label: "Guitar" },
  { value: "bass", label: "Bass" },
  { value: "drums", label: "Drums" },
  { value: "pro_guitar", label: "Pro Guitar" },
  { value: "pro_bass", label: "Pro Bass" },
  { value: "pro_drums", label: "Pro Drums" },
];

export default function MainSearchPage() {
  const [tracks, setTracks] = useState([]);
  const [search, setSearch] = useState("");
  const [ownedOnly, setOwnedOnly] = useState(false);
  const [ownedIds, setOwnedIds] = useState(() => loadOwnedTrackIds());
  const [instrument, setInstrument] = useState("drums");
  const [minDifficulty, setMinDifficulty] = useState(0);
  const [sortMode, setSortMode] = useState("difficulty_desc");
  const [loading, setLoading] = useState(false);
  const [errorMessage, setErrorMessage] = useState("");

  async function loadTracks() {
    setLoading(true);
    setErrorMessage("");

    let query = supabase
      .from("v_tracks_search_with_difficulties")
      .select(
        "track_id, epic_slug, title, artist_display, album_art_url, bpm, musical_key, mode, camelot_code, duration_seconds, rating_code, band, vocals, guitar, bass, drums, pro_guitar, pro_bass, pro_drums"
      )
      .limit(MAIN_RESULT_LIMIT);

    if (search.trim()) {
      const value = `%${search.trim()}%`;
      query = query.or(
        `title.ilike.${value},artist_display.ilike.${value},epic_slug.ilike.${value}`
      );
    }

    if (Number(minDifficulty) > 0) {
      query = query.gte(instrument, Number(minDifficulty));
    }

    if (sortMode === "difficulty_desc") {
      query = query
        .order(instrument, { ascending: false, nullsFirst: false })
        .order("title");
    } else if (sortMode === "length_asc") {
      query = query.order("duration_seconds", { ascending: true }).order("title");
    } else if (sortMode === "length_desc") {
      query = query.order("duration_seconds", { ascending: false }).order("title");
    } else {
      query = query.order("title", { ascending: true });
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
      loadTracks();
    }, SEARCH_DEBOUNCE_MS);

    return () => clearTimeout(timeout);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [search, instrument, minDifficulty, sortMode]);

  const visibleTracks = useMemo(() => {
    if (!ownedOnly) return tracks;
    return tracks.filter((track) => ownedIds.has(Number(track.track_id)));
  }, [tracks, ownedOnly, ownedIds]);

  function handleSubmit(event) {
    event.preventDefault();
    loadTracks();
  }

  function handleToggleOwned(trackId) {
    const next = toggleOwnedTrackId(trackId);
    setOwnedIds(new Set(next));
  }

  return (
    <section className="page">
      <div className="tab-header">
        <div>
          <p className="eyebrow">Main Search</p>
          <h1>Chart and difficulty search</h1>
          <p className="muted">
            Search by song or artist, then filter/sort by instrument difficulty and song length.
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

      <form onSubmit={handleSubmit} className="panel main-search-controls">
        <input
          className="input wide"
          value={search}
          onChange={(event) => setSearch(event.target.value)}
          placeholder="Search title, artist, or slug..."
        />

        <select
          className="input"
          value={instrument}
          onChange={(event) => setInstrument(event.target.value)}
        >
          {INSTRUMENTS.map((item) => (
            <option key={item.value} value={item.value}>
              {item.label}
            </option>
          ))}
        </select>

        <select
          className="input"
          value={minDifficulty}
          onChange={(event) => setMinDifficulty(Number(event.target.value))}
        >
          <option value={0}>Any difficulty</option>
          <option value={1}>1+</option>
          <option value={2}>2+</option>
          <option value={3}>3+</option>
          <option value={4}>4+</option>
          <option value={5}>5+</option>
          <option value={6}>6+</option>
        </select>

        <select
          className="input"
          value={sortMode}
          onChange={(event) => setSortMode(event.target.value)}
        >
          <option value="difficulty_desc">Sort by selected difficulty</option>
          <option value="length_asc">Shortest first</option>
          <option value="length_desc">Longest first</option>
          <option value="title">Title A-Z</option>
        </select>

        <button className="btn primary" type="submit">
          Search
        </button>
      </form>

      <div className="result-bar">
        {loading ? "Loading tracks..." : `${visibleTracks.length} shown / ${tracks.length} loaded`}
        {tracks.length >= MAIN_RESULT_LIMIT && (
          <span className="muted">Showing first {MAIN_RESULT_LIMIT} matches</span>
        )}
        {errorMessage && <span className="error">Error: {errorMessage}</span>}
      </div>

      <section className="track-grid">
        {visibleTracks.map((track) => (
          <TrackCard
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