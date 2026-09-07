import { useEffect, useState, useCallback } from "react";
import { api } from "../api";
import { useAuth } from "../context/AuthContext";
import Loading from "../components/Loading";
import ErrorMessage from "../components/ErrorMessage";

const STATUS_LABELS = {
  want_to_read: "Want to Read",
  reading: "Reading",
  finished: "Finished",
};

export default function DashboardPage() {
  const { subscribeToEvents } = useAuth();
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const load = useCallback(() => {
    setLoading(true);
    setError("");
    api
      .dashboard()
      .then(setData)
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false));
  }, []);

  useEffect(load, [load]);

  useEffect(() => {
    // Any live activity event could change dashboard counts (a lend, a
    // shelf share, a finished book) so just refetch the summary.
    return subscribeToEvents((event) => {
      if (event.type === "activity") load();
    });
  }, [subscribeToEvents, load]);

  if (loading) return <Loading label="Loading your dashboard..." />;
  if (error) return <ErrorMessage message={error} onRetry={load} />;
  if (!data) return null;

  return (
    <div className="page">
      <h1>Dashboard</h1>
      <div className="stat-grid">
        {Object.entries(data.counts_by_status).map(([status, count]) => (
          <div key={status} className="card stat-card">
            <span className="stat-value">{count}</span>
            <span className="stat-label">{STATUS_LABELS[status] || status}</span>
          </div>
        ))}
        <div className="card stat-card">
          <span className="stat-value">{data.finished_this_year}</span>
          <span className="stat-label">Finished this year</span>
        </div>
        <div className="card stat-card">
          <span className="stat-value">{data.average_rating ?? "-"}</span>
          <span className="stat-label">Average rating</span>
        </div>
        <div className="card stat-card">
          <span className="stat-value">{data.top_shelf ?? "-"}</span>
          <span className="stat-label">Biggest shelf</span>
        </div>
        <div className="card stat-card">
          <span className="stat-value">{data.books_lent_out}</span>
          <span className="stat-label">Books lent out</span>
        </div>
        <div className="card stat-card">
          <span className="stat-value">{data.shelves_shared_with_me}</span>
          <span className="stat-label">Shelves shared with me</span>
        </div>
      </div>

      <h2>Recent activity</h2>
      {data.recent_activity.length === 0 ? (
        <p className="muted">Nothing yet - add a book to get started.</p>
      ) : (
        <ul className="activity-feed">
          {data.recent_activity.map((entry) => (
            <li key={entry.id}>
              <span>{entry.message}</span>
              <span className="muted small">{new Date(entry.created_at).toLocaleString()}</span>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
