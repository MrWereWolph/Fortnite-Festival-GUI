export default function TrackCard({ track, owned, onToggleOwned }) {
  const title = track.title ?? "Unknown Title";
  const artist = track.artist_display ?? "Unknown Artist";
  const art = track.album_art_url;
  const bpm = track.bpm ?? "—";
  const key = track.musical_key ?? "";
  const mode = track.mode ?? "";
  const camelot = track.camelot_code ?? "—";
  const rating = track.rating_code ?? "";
  const duration = track.duration_seconds
    ? `${Math.floor(track.duration_seconds / 60)}:${String(track.duration_seconds % 60).padStart(2, "0")}`
    : "—";

  return (
    <article className={`track-card ${owned ? "track-card-owned" : ""}`}>
      <div className="track-art-wrap">
        {art ? (
          <img
            src={art}
            alt={`${title} album art`}
            className="track-art"
            loading="lazy"
            decoding="async"
          />
        ) : (
          <div className="track-art track-art-empty">No Art</div>
        )}

        <div className="card-actions">
          <button
            type="button"
            className={`locker-btn ${owned ? "owned" : ""}`}
            onClick={(event) => {
              event.preventDefault();
              event.stopPropagation();
              onToggleOwned(track.track_id);
            }}
          >
            {owned ? "✓ Locker" : "+ Locker"}
          </button>
        </div>
      </div>

      <div className="track-info">
        <h2>{title}</h2>
        <p>{artist}</p>

        <div className="track-meta">
          <span>{bpm} BPM</span>
          <span>{key} {mode}</span>
          <span>{camelot}</span>
          {rating && <span>{rating}</span>}
          <span>{duration}</span>
        </div>
      </div>
    </article>
  );
}
