export default function ExportPage() {
  return (
    <section className="page">
      <p className="eyebrow">Export</p>
      <h1>Catalog exports</h1>
      <p className="muted">
        CSV, JSON, and database exports will live here. First target: export v_tracks_export as CSV.
      </p>

      <div className="panel">
        <h2>Planned exports</h2>
        <ul className="muted-list">
          <li>Full track catalog CSV</li>
          <li>Main Stage difficulties CSV</li>
          <li>Owned tracks export</li>
          <li>Developer JSON export</li>
          <li>SQLite database download later</li>
        </ul>
      </div>
    </section>
  );
}
