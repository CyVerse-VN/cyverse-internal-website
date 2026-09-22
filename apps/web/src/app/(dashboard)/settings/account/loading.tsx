export default function AccountSettingsLoading() {
  return (
    <main className="settings-page route-loading" aria-busy="true">
      <span className="sr-only" role="status">Loading account settings…</span>
      <div className="loading-heading">
        <span className="skeleton skeleton--eyebrow" />
        <span className="skeleton skeleton--title" />
        <span className="skeleton skeleton--copy" />
      </div>
      <div className="settings-grid" aria-hidden="true">
        <span className="skeleton skeleton--settings-summary" />
        <div className="settings-sections">
          <span className="skeleton skeleton--settings-card" />
          <span className="skeleton skeleton--settings-card" />
        </div>
      </div>
    </main>
  );
}
