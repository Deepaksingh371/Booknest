import { useCallback, useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../api";
import { useAuth } from "../context/AuthContext";
import Loading from "../components/Loading";
import ErrorMessage from "../components/ErrorMessage";

export default function ShelvesPage() {
  const { subscribeToEvents } = useAuth();
  const [shelves, setShelves] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [newName, setNewName] = useState("");
  const [creating, setCreating] = useState(false);
  const [createError, setCreateError] = useState("");

  const load = useCallback(() => {
    setLoading(true);
    setError("");
    api
      .listShelves()
      .then(setShelves)
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false));
  }, []);

  useEffect(load, [load]);
  useEffect(() => subscribeToEvents((event) => {
    if (event.type === "activity") load();
  }), [subscribeToEvents, load]);

  async function handleCreate(e) {
    e.preventDefault();
    setCreateError("");
    if (!newName.trim()) {
      setCreateError("Shelf name is required");
      return;
    }
    setCreating(true);
    try {
      await api.createShelf(newName.trim());
      setNewName("");
      load();
    } catch (err) {
      setCreateError(err.message);
    } finally {
      setCreating(false);
    }
  }

  async function handleDelete(id) {
    if (!confirm("Delete this shelf? Books on it will not be deleted.")) return;
    await api.deleteShelf(id);
    load();
  }

  return (
    <div className="page">
      <h1>My Shelves</h1>

      <form className="card form inline-form" onSubmit={handleCreate}>
        <input
          placeholder="New shelf name"
          value={newName}
          onChange={(e) => setNewName(e.target.value)}
          disabled={creating}
        />
        <button type="submit" className="btn btn-primary" disabled={creating}>
          {creating ? "Creating..." : "+ Create Shelf"}
        </button>
        {createError && <span className="field-error">{createError}</span>}
      </form>

      {loading ? (
        <Loading label="Loading shelves..." />
      ) : error ? (
        <ErrorMessage message={error} onRetry={load} />
      ) : shelves.length === 0 ? (
        <p className="muted">You haven't created any shelves yet.</p>
      ) : (
        <div className="card-grid">
          {shelves.map((shelf) => (
            <div key={shelf.id} className="card shelf-card">
              <h3>
                <Link to={`/shelves/${shelf.id}`}>{shelf.name}</Link>
              </h3>
              <p className="muted small">{shelf.book_count} book(s)</p>
              <button type="button" className="btn btn-small btn-danger" onClick={() => handleDelete(shelf.id)}>
                Delete
              </button>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
