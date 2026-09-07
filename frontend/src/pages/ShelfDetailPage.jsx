import { useCallback, useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import { api } from "../api";
import { useAuth } from "../context/AuthContext";
import BookCard from "../components/BookCard";
import Loading from "../components/Loading";
import ErrorMessage from "../components/ErrorMessage";

export default function ShelfDetailPage() {
  const { shelfId } = useParams();
  const { subscribeToEvents } = useAuth();

  const [shelfMeta, setShelfMeta] = useState(null);
  const [books, setBooks] = useState([]);
  const [collaborators, setCollaborators] = useState([]);
  const [myBooks, setMyBooks] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const [shareEmail, setShareEmail] = useState("");
  const [shareRole, setShareRole] = useState("viewer");
  const [shareBusy, setShareBusy] = useState(false);
  const [shareError, setShareError] = useState("");
  const [pickBookId, setPickBookId] = useState("");

  const load = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      const [mine, shared, shelfBooks] = await Promise.all([
        api.listShelves(),
        api.sharedWithMe(),
        api.shelfBooks(shelfId),
      ]);
      const meta = [...mine, ...shared].find((s) => s.id === shelfId);
      if (!meta) throw new Error("Shelf not found or you don't have access");
      setShelfMeta(meta);
      setBooks(shelfBooks);
      if (meta.my_role === "owner") {
        const collabs = await api.collaborators(shelfId);
        setCollaborators(collabs);
      }
      if (meta.my_role === "owner" || meta.my_role === "editor") {
        const mineBooks = await api.listBooks({ page: 1, page_size: 100 });
        setMyBooks(mineBooks.items);
      }
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }, [shelfId]);

  useEffect(() => {
    load();
  }, [load]);

  useEffect(
    () =>
      subscribeToEvents((event) => {
        if (event.type === "activity") load();
      }),
    [subscribeToEvents, load]
  );

  async function handleShare(e) {
    e.preventDefault();
    setShareError("");
    if (!shareEmail.trim()) {
      setShareError("Enter an email");
      return;
    }
    setShareBusy(true);
    try {
      await api.shareShelf(shelfId, shareEmail.trim(), shareRole);
      setShareEmail("");
      load();
    } catch (err) {
      setShareError(err.message);
    } finally {
      setShareBusy(false);
    }
  }

  async function handleRoleChange(userId, role) {
    await api.updateRole(shelfId, userId, role);
    load();
  }

  async function handleRemoveCollaborator(userId) {
    await api.removeCollaborator(shelfId, userId);
    load();
  }

  async function handleAddBook() {
    if (!pickBookId) return;
    await api.addBookToShelf(shelfId, pickBookId);
    setPickBookId("");
    load();
  }

  async function handleRemoveBook(bookId) {
    await api.removeBookFromShelf(shelfId, bookId);
    load();
  }

  if (loading) return <Loading label="Loading shelf..." />;
  if (error) return <ErrorMessage message={error} onRetry={load} />;
  if (!shelfMeta) return null;

  const canEdit = shelfMeta.my_role === "owner" || shelfMeta.my_role === "editor";
  const isOwner = shelfMeta.my_role === "owner";
  const booksAvailableToAdd = myBooks.filter((b) => !books.some((sb) => sb.id === b.id));

  return (
    <div className="page">
      <div className="page-header">
        <h1>{shelfMeta.name}</h1>
        <span className="badge">{shelfMeta.my_role}</span>
      </div>
      <p className="muted small">Owned by {shelfMeta.owner_email}</p>

      {canEdit && (
        <div className="card inline-form">
          <select value={pickBookId} onChange={(e) => setPickBookId(e.target.value)}>
            <option value="">Choose one of your books to add...</option>
            {booksAvailableToAdd.map((b) => (
              <option key={b.id} value={b.id}>
                {b.title}
              </option>
            ))}
          </select>
          <button type="button" className="btn btn-primary btn-small" onClick={handleAddBook} disabled={!pickBookId}>
            Add to shelf
          </button>
        </div>
      )}

      {books.length === 0 ? (
        <p className="muted">No books on this shelf yet.</p>
      ) : (
        <div className="card-grid">
          {books.map((book) => (
            <BookCard
              key={book.id}
              book={book}
              readOnly
              onRemoveFromShelf={canEdit ? handleRemoveBook : undefined}
            />
          ))}
        </div>
      )}

      {isOwner && (
        <>
          <h2>Sharing</h2>
          <form className="card inline-form" onSubmit={handleShare}>
            <input
              type="email"
              placeholder="Collaborator email"
              value={shareEmail}
              onChange={(e) => setShareEmail(e.target.value)}
              disabled={shareBusy}
            />
            <select value={shareRole} onChange={(e) => setShareRole(e.target.value)} disabled={shareBusy}>
              <option value="viewer">Viewer</option>
              <option value="editor">Editor</option>
            </select>
            <button type="submit" className="btn btn-small btn-primary" disabled={shareBusy}>
              {shareBusy ? "Sharing..." : "Share"}
            </button>
            {shareError && <span className="field-error">{shareError}</span>}
          </form>

          {collaborators.length > 0 && (
            <ul className="collaborator-list">
              {collaborators.map((c) => (
                <li key={c.user_id}>
                  <span>
                    {c.name} ({c.email})
                  </span>
                  <select value={c.role} onChange={(e) => handleRoleChange(c.user_id, e.target.value)}>
                    <option value="viewer">Viewer</option>
                    <option value="editor">Editor</option>
                  </select>
                  <button
                    type="button"
                    className="btn btn-small btn-danger"
                    onClick={() => handleRemoveCollaborator(c.user_id)}
                  >
                    Remove
                  </button>
                </li>
              ))}
            </ul>
          )}
        </>
      )}
    </div>
  );
}
