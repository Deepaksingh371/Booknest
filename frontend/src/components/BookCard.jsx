import { useState } from "react";

const STATUS_LABELS = {
  want_to_read: "Want to Read",
  reading: "Reading",
  finished: "Finished",
};

function ActionButton({ label, busyLabel, onClick, className = "btn btn-small" }) {
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  async function handle() {
    setError("");
    setBusy(true);
    try {
      await onClick();
    } catch (err) {
      setError(err.message || "Failed");
    } finally {
      setBusy(false);
    }
  }
  return (
    <span className="inline-action">
      <button type="button" className={className} onClick={handle} disabled={busy}>
        {busy ? busyLabel || "Working..." : label}
      </button>
      {error && <span className="field-error">{error}</span>}
    </span>
  );
}

export default function BookCard({
  book,
  onEdit,
  onDelete,
  onLogProgress,
  onLend,
  onReturn,
  onAddToShelf,
  onRemoveFromShelf,
  readOnly,
}) {
  const [progressInput, setProgressInput] = useState(book.current_page ?? 0);
  const [progressError, setProgressError] = useState("");
  const [lendEmail, setLendEmail] = useState("");

  const pct =
    book.total_pages && book.current_page != null
      ? Math.min(100, Math.round((book.current_page / book.total_pages) * 100))
      : null;

  return (
    <div className="card book-card">
      <div className="book-card-header">
        <div>
          <h3>{book.title}</h3>
          <p className="muted">{book.author}</p>
        </div>
        <span className={`badge badge-${book.status}`}>{STATUS_LABELS[book.status]}</span>
      </div>

      {book.owner_email && <p className="muted small">Owned by {book.owner_name || book.owner_email}</p>}
      {book.rating && <p className="small">Rating: {"★".repeat(book.rating)}</p>}
      {book.notes && <p className="small notes">{book.notes}</p>}

      {book.total_pages != null && pct !== null && (
        <div className="progress-bar">
          <div className="progress-fill" style={{ width: `${pct}%` }} />
          <span className="progress-label">
            {book.current_page}/{book.total_pages} pages ({pct}%)
          </span>
        </div>
      )}

      {book.is_lent && <p className="notice">Currently lent to {book.lent_to_email}</p>}

      {!readOnly && (onEdit || onDelete) && (
        <div className="book-card-actions">
          {onEdit && (
            <button type="button" className="btn btn-small" onClick={() => onEdit(book)}>
              Edit
            </button>
          )}
          {onDelete && <ActionButton label="Delete" busyLabel="Deleting..." onClick={() => onDelete(book.id)} />}
        </div>
      )}

      {!readOnly && onLogProgress && book.total_pages != null && book.status !== "finished" && (
        <div className="inline-form">
          <input
            type="number"
            value={progressInput}
            min={0}
            max={book.total_pages}
            onChange={(e) => setProgressInput(e.target.value)}
          />
          <ActionButton
            label="Log progress"
            busyLabel="Saving..."
            onClick={async () => {
              setProgressError("");
              try {
                await onLogProgress(book.id, Number(progressInput));
              } catch (err) {
                setProgressError(err.message);
                throw err;
              }
            }}
          />
          {progressError && <span className="field-error">{progressError}</span>}
        </div>
      )}

      {!readOnly && onLend && !book.is_lent && (
        <div className="inline-form">
          <input
            type="email"
            placeholder="Lend to email"
            value={lendEmail}
            onChange={(e) => setLendEmail(e.target.value)}
          />
          <ActionButton label="Lend" busyLabel="Lending..." onClick={() => onLend(book.id, lendEmail)} />
        </div>
      )}
      {!readOnly && onReturn && book.is_lent && (
        <ActionButton label="Mark returned" busyLabel="Updating..." onClick={() => onReturn(book.id)} />
      )}

      {onAddToShelf && (
        <ActionButton label="Add to shelf" busyLabel="Adding..." onClick={() => onAddToShelf(book.id)} />
      )}
      {onRemoveFromShelf && !readOnly && (
        <ActionButton
          label="Remove from shelf"
          busyLabel="Removing..."
          className="btn btn-small btn-danger"
          onClick={() => onRemoveFromShelf(book.id)}
        />
      )}
    </div>
  );
}
