import { useEffect, useState } from "react";
import { supabase } from "./lib/supabaseClient";
import "./App.css";

export default function App() {
  const [tracks, setTracks] = useState([]);
  const [search, setSearch] = useState("");
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
      .limit(24);

    if (searchText.trim()) {
      const value = `%${searchText.trim()}%`;
      query = query.or(`title.ilike.${value},artist_display.ilike.${value}`);
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
    loadTracks();
  }, []);

  function handleSubmit(event) {
    event.preventDefault();
    loadTracks(search);
  }

  return (
    <main className="app-shell">
      <section className="hero">
        <p className="eyebrow">FNFest GUI5</p>
        <h1>Fortnite Festival Jam Search</h1>
        <p>
          Search tracks by title or artist using the Supabase-backed GUI5 catalog.
        </p>

        <form onSubmit={handleSubmit} className="search-form">
          <input
            value={search}
            onChange={(event) => setSearch(event.target.value)}
            placeholder="Search title or artist..."
          />
          <button type="submit">Search</button>
        </form>
      </section>

      {loading && <p className="status">Loading tracks...</p>}
      {errorMessage && <p className="error">Error: {errorMessage}</p>}

      <section className="track-grid">
        {tracks.map((track) => (
          <article key={track.track_id} className="track-card">
            {track.album_art_url && (
              <img src={track.album_art_url} alt={`${track.title} album art`} />
            )}

            <div className="track-info">
              <h2>{track.title}</h2>
              <p>{track.artist_display}</p>

              <div className="track-meta">
                <span>{track.bpm} BPM</span>
                <span>
                  {track.musical_key} {track.mode}
                </span>
                <span>{track.camelot_code ?? "—"}</span>
                <span>{track.rating_code}</span>
              </div>
            </div>
          </article>
        ))}
      </section>
    </main>
  );
}