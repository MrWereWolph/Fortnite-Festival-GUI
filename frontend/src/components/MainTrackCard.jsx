import DifficultyBars from "./DifficultyBars";

function formatDuration(seconds) {
  if (!seconds && seconds !== 0) return "—";

  const minutes = Math.floor(seconds / 60);
  const remainingSeconds = String(seconds % 60).padStart(2, "0");

  return `${minutes}:${remainingSeconds}`;
}

const DIFFICULTY_ROWS = [
  { label: "Vocals", field: "vocals" },
  { label: "Lead", field: "guitar" },
  { label: "Bass", field: "bass" },
  { label: "Drums", field: "drums" },
  { label: "Pro Vocals", field: "band" },
  { label: "Pro Lead", field: "pro_guitar" },
  { label: "Pro Bass", field: "pro_bass" },
  { label: "Pro Drums", field: "pro_drums" },
];

export default function MainTrackCard({ track, owned, onToggleOwned }) {
  const title = track.title ?? "Unknown Title";
  const artist = track.artist_display ?? "Unknown Artist";
  const art = track.album_art_url;
  const duration = formatDuration(track.duration_seconds);

  return (
    <article className={`track-card main-track-card ${owned ? "track-card-owned" : ""}`}>
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

        <div className="main-meta">
          <span>{duration}</span>
        </div>

        <div className="difficulty-list">
          {DIFFICULTY_ROWS.map((row) => (
            <DifficultyBars
              key={row.field}
              label={row.label}
              value={track[row.field]}
            />
          ))}
        </div>
      </div>
    </article>
  );
}