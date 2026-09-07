import { useCallback, useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../api";
import { useAuth } from "../context/AuthContext";
import Loading from "../components/Loading";
import ErrorMessage from "../components/ErrorMessage";

export default function SharedWithMePage() {
  const { subscribeToEvents } = useAuth();
  const [shelves, setShelves] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const load = useCallback(() => {
    setLoading(true);
    setError("");
    api
      .sharedWithMe()
      .then(setShelves)
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false));
  }, []);

  useEffect(load, [load]);
  useEffect(() => subscribeToEvents((event) => {
    if (event.type === "activity") load();
  }), [subscribeToEvents, load]);

  if (loading) return <Loading label="Loading shared shelves..." />;
  if (error) return <ErrorMessage message={error} onRetry={load} />;

  return (
    <div className="page">
      <h1>Shared With Me</h1>
      {shelves.length === 0 ? (
        <p className="muted">No one has shared a shelf with you yet.</p>
      ) : (
        <div className="card-grid">
          {shelves.map((shelf) => (
            <div key={shelf.id} className="card shelf-card">
              <h3>
                <Link to={`/shelves/${shelf.id}`}>{shelf.name}</Link>
              </h3>
              <p className="muted small">Owned by {shelf.owner_email}</p>
              <span className="badge">{shelf.my_role}</span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
