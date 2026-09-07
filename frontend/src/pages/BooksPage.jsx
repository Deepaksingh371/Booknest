import { useCallback, useEffect, useState } from "react";
import { api } from "../api";
import { useAuth } from "../context/AuthContext";
import BookCard from "../components/BookCard";
import BookForm from "../components/BookForm";
import Loading from "../components/Loading";
import ErrorMessage from "../components/ErrorMessage";

const PAGE_SIZE = 8;

export default function BooksPage() {
  const { subscribeToEvents } = useAuth();
  const [books, setBooks] = useState([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [status, setStatus] = useState("");
  const [search, setSearch] = useState("");
  const [sortBy, setSortBy] = useState("created_at");
  const [sortDir, setSortDir] = useState("desc");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [showForm, setShowForm] = useState(false);
  const [editingBook, setEditingBook] = useState(null);

  const load = useCallback(() => {
    setLoading(true);
    setError("");
    const params = { page, page_size: PAGE_SIZE, sort_by: sortBy, sort_dir: sortDir };
    if (status) params.status = status;
    if (search) params.search = search;
    api
      .listBooks(params)
      .then((data) => {
        setBooks(data.items);
        setTotal(data.total);
      })
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false));
  }, [page, status, search, sortBy, sortDir]);

  useEffect(load, [load]);

  useEffect(() => subscribeToEvents((event) => {
    if (event.type === "activity") load();
  }), [subscribeToEvents, load]);

  async function handleCreate(payload) {
    await api.createBook(payload);
    setShowForm(false);
    load();
  }

  async function handleUpdate(payload) {
    await api.updateBook(editingBook.id, payload);
    setEditingBook(null);
    load();
  }

  async function handleDelete(id) {
    await api.deleteBook(id);
    load();
  }

  async function handleLogProgress(id, currentPage) {
    await api.logProgress(id, currentPage);
    load();
  }

  async function handleLend(id, email) {
    if (!email) throw new Error("Enter an email to lend to");
    await api.lendBook(id, email);
    load();
  }

  async function handleReturn(id) {
    await api.returnBook(id);
    load();
  }

  const totalPages = Math.max(1, Math.ceil(total / PAGE_SIZE));

  return (
    <div className="page">
      <div className="page-header">
        <h1>My Books</h1>
        <button type="button" className="btn btn-primary" onClick={() => setShowForm((v) => !v)}>
          {showForm ? "Close" : "+ Add Book"}
        </button>
      </div>

      {showForm && <BookForm onSubmit={handleCreate} onCancel={() => setShowForm(false)} />}
      {editingBook && (
        <BookForm initial={editingBook} onSubmit={handleUpdate} onCancel={() => setEditingBook(null)} />
      )}

      <div className="toolbar">
        <select
          value={status}
          onChange={(e) => {
            setStatus(e.target.value);
            setPage(1);
          }}
        >
          <option value="">All statuses</option>
          <option value="want_to_read">Want to Read</option>
          <option value="reading">Reading</option>
          <option value="finished">Finished</option>
        </select>
        <input
          type="search"
          placeholder="Search title or author..."
          value={search}
          onChange={(e) => {
            setSearch(e.target.value);
            setPage(1);
          }}
        />
        <select value={sortBy} onChange={(e) => setSortBy(e.target.value)}>
          <option value="created_at">Date added</option>
          <option value="title">Title</option>
          <option value="rating">Rating</option>
        </select>
        <select value={sortDir} onChange={(e) => setSortDir(e.target.value)}>
          <option value="desc">Descending</option>
          <option value="asc">Ascending</option>
        </select>
      </div>

      {loading ? (
        <Loading label="Loading books..." />
      ) : error ? (
        <ErrorMessage message={error} onRetry={load} />
      ) : books.length === 0 ? (
        <p className="muted">No books match your filters yet.</p>
      ) : (
        <>
          <div className="card-grid">
            {books.map((book) => (
              <BookCard
                key={book.id}
                book={book}
                onEdit={setEditingBook}
                onDelete={handleDelete}
                onLogProgress={handleLogProgress}
                onLend={handleLend}
                onReturn={handleReturn}
              />
            ))}
          </div>
          <div className="pagination">
            <button className="btn btn-small" disabled={page <= 1} onClick={() => setPage((p) => p - 1)}>
              Previous
            </button>
            <span>
              Page {page} of {totalPages}
            </span>
            <button
              className="btn btn-small"
              disabled={page >= totalPages}
              onClick={() => setPage((p) => p + 1)}
            >
              Next
            </button>
          </div>
        </>
      )}
    </div>
  );
}
