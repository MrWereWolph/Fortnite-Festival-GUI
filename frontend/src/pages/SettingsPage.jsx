import { clearOwnedTrackIds } from "../lib/ownedTracks";

export default function SettingsPage() {
  function clearOwned() {
    clearOwnedTrackIds();
    window.location.reload();
  }

  return (
    <section className="page">
      <p className="eyebrow">Settings</p>
      <h1>Local settings</h1>
      <p className="muted">
        These settings are local to this browser until account sync is added.
      </p>

      <div className="panel settings-panel">
        <div>
          <h2>Owned / Locker tracks</h2>
          <p className="muted">
            Clear locally stored owned tracks from this browser.
          </p>
        </div>

        <button className="btn danger" type="button" onClick={clearOwned}>
          Clear owned tracks
        </button>
      </div>
    </section>
  );
}
