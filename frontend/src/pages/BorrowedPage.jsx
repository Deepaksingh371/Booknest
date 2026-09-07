import { useCallback, useEffect, useState } from "react";
import { api } from "../api";
import { useAuth } from "../context/AuthContext";
import BookCard from "../components/BookCard";
import Loading from "../components/Loading";
import ErrorMessage from "../components/ErrorMessage";

export default function BorrowedPage() {
  const { subscribeToEvents } = useAuth();
  const [books, setBooks] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const load = useCallback(() => {
    setLoading(true);
    setError("");
    api
      .borrowed()
      .then(setBooks)
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false));
  }, []);

  useEffect(load, [load]);

  useEffect(
    () =>
      // Live: appears when lent to us, disappears the moment it's returned.
      subscribeToEvents((event) => {
        if (event.type === "activity") load();
      }),
    [subscribeToEvents, load]
  );

  if (loading) return <Loading label="Loading borrowed books..." />;
  if (error) return <ErrorMessage message={error} onRetry={load} />;

  return (
    <div className="page">
      <h1>Borrowed From Others</h1>
      {books.length === 0 ? (
        <p className="muted">No one has lent you a book right now.</p>
      ) : (
        <div className="card-grid">
          {books.map((book) => (
            <BookCard key={book.id} book={book} readOnly />
          ))}
        </div>
      )}
    </div>
  );
}
