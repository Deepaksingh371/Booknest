import { useCallback, useEffect, useState } from "react";
import { api } from "../api";
import Loading from "../components/Loading";
import ErrorMessage from "../components/ErrorMessage";

const PAGE_SIZE = 8;

function PoolCard({ entry, onAdd }) {
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [added, setAdded] = useState(entry.in_library);

  async function handleAdd() {
    setBusy(true);
    setError("");
    try {
      await onAdd(entry.id);
      setAdded(true);
    } catch (err) {
      setError(err.message || "Couldn't add this book");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="card pool-card">
      <div className="pool-cover" style={{ background: entry.cover_color || "#fb4d0a" }}>
        <span>{entry.title.slice(0, 1)}</span>
      </div>
      <div className="pool-body">
        <h3>{entry.title}</h3>
        <p className="muted small">{entry.author}</p>
        {entry.genre && <span className="badge pool-genre">{entry.genre}</span>}
        {entry.description && <p className="small notes">{entry.description}</p>}
        {entry.total_pages && <p className="muted small">{entry.total_pages} pages</p>}
        <button
          type="button"
          className={`btn btn-small ${added ? "" : "btn-primary"}`}
          onClick={handleAdd}
          disabled={busy || added}
        >
          {added ? "In your library ✓" : busy ? "Adding..." : "+ Add to my library"}
        </button>
        {error && <div className="field-error">{error}</div>}
      </div>
    </div>
  );
}

export default function BookPoolPage() {
  const [items, setItems] = useState([]);
  const [genres, setGenres] = useState([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [search, setSearch] = useState("");
  const [genre, setGenre] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const load = useCallback(() => {
    setLoading(true);
    setError("");
    const params = { page, page_size: PAGE_SIZE };
    if (search) params.search = search;
    if (genre) params.genre = genre;
    api
      .browseCatalog(params)
      .then((data) => {
        setItems(data.items);
        setTotal(data.total);
        setGenres(data.genres);
      })
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false));
  }, [page, search, genre]);

  useEffect(load, [load]);

  async function handleAdd(catalogId) {
    await api.addFromCatalog(catalogId);
  }

  const totalPages = Math.max(1, Math.ceil(total / PAGE_SIZE));

  return (
    <div className="page">
      <div className="page-header">
        <div>
          <h1>Book Pool</h1>
          <p className="muted small">Browse the shared catalog and add anything that catches your eye.</p>
        </div>
      </div>

      <div className="toolbar">
        <input
          type="search"
          placeholder="Search title or author..."
          value={search}
          onChange={(e) => {
            setSearch(e.target.value);
            setPage(1);
          }}
        />
        <select
          value={genre}
          onChange={(e) => {
            setGenre(e.target.value);
            setPage(1);
          }}
        >
          <option value="">All genres</option>
          {genres.map((g) => (
            <option key={g} value={g}>
              {g}
            </option>
          ))}
        </select>
      </div>

      {loading ? (
        <Loading label="Loading the book pool..." />
      ) : error ? (
        <ErrorMessage message={error} onRetry={load} />
      ) : items.length === 0 ? (
        <p className="muted">No books match that search.</p>
      ) : (
        <>
          <div className="pool-grid">
            {items.map((entry) => (
              <PoolCard key={entry.id} entry={entry} onAdd={handleAdd} />
            ))}
          </div>
          <div className="pagination">
            <button className="btn btn-small" disabled={page <= 1} onClick={() => setPage((p) => p - 1)}>
              Previous
            </button>
            <span>
              Page {page} of {totalPages}
            </span>
            <button className="btn btn-small" disabled={page >= totalPages} onClick={() => setPage((p) => p + 1)}>
              Next
            </button>
          </div>
        </>
      )}
    </div>
  );
}
