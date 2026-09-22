export default function DashboardLoading() {
  return (
    <main className="dashboard-page route-loading" aria-busy="true">
      <span className="sr-only" role="status">Loading dashboard…</span>
      <header className="topbar">
        <span className="skeleton skeleton--dashboard-search" />
        <span className="skeleton skeleton--profile" />
      </header>
      <div className="dashboard-body" aria-hidden="true">
        <div className="loading-heading">
          <span className="skeleton skeleton--eyebrow" />
          <span className="skeleton skeleton--title" />
          <span className="skeleton skeleton--copy" />
        </div>
        <div className="metric-grid">
          {Array.from({ length: 4 }, (_, index) => (
            <span className="skeleton skeleton--metric" key={index} />
          ))}
        </div>
        <section className="dashboard-section">
          <span className="skeleton skeleton--section-title" />
          <div className="tool-grid">
            {Array.from({ length: 4 }, (_, index) => (
              <span className="skeleton skeleton--tool" key={index} />
            ))}
          </div>
        </section>
      </div>
    </main>
  );
}
