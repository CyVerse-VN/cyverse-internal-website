export default function UsersLoading() {
  return (
    <main className="admin-page route-loading" aria-busy="true">
      <span className="sr-only" role="status">Loading users…</span>
      <header className="admin-header">
        <div className="loading-heading">
          <span className="skeleton skeleton--eyebrow" />
          <span className="skeleton skeleton--title" />
          <span className="skeleton skeleton--copy" />
        </div>
        <span className="skeleton skeleton--button" />
      </header>
      <section className="admin-card admin-card--loading">
        <div className="user-search">
          <span className="skeleton skeleton--search" />
          <span className="skeleton skeleton--button" />
        </div>
        <div className="loading-table" aria-hidden="true">
          <span className="skeleton skeleton--table-header" />
          {Array.from({ length: 6 }, (_, index) => (
            <span className="skeleton skeleton--table-row" key={index} />
          ))}
        </div>
      </section>
    </main>
  );
}
