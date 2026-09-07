import { useState } from "react";

const STATUS_OPTIONS = [
  { value: "want_to_read", label: "Want to Read" },
  { value: "reading", label: "Reading" },
  { value: "finished", label: "Finished" },
];

export default function BookForm({ initial, onSubmit, onCancel }) {
  const [title, setTitle] = useState(initial?.title || "");
  const [author, setAuthor] = useState(initial?.author || "");
  const [status, setStatus] = useState(initial?.status || "want_to_read");
  const [totalPages, setTotalPages] = useState(initial?.total_pages ?? "");
  const [rating, setRating] = useState(initial?.rating ?? "");
  const [notes, setNotes] = useState(initial?.notes || "");
  const [errors, setErrors] = useState({});
  const [submitting, setSubmitting] = useState(false);
  const [formError, setFormError] = useState("");

  function validate() {
    const errs = {};
    if (!title.trim()) errs.title = "Title is required";
    if (!author.trim()) errs.author = "Author is required";
    if (totalPages !== "" && Number(totalPages) <= 0) errs.totalPages = "Total pages must be positive";
    if (rating !== "" && (Number(rating) < 1 || Number(rating) > 5)) errs.rating = "Rating must be 1-5";
    setErrors(errs);
    return Object.keys(errs).length === 0;
  }

  async function handleSubmit(e) {
    e.preventDefault();
    setFormError("");
    if (!validate()) return;
    setSubmitting(true);
    try {
      await onSubmit({
        title,
        author,
        status,
        total_pages: totalPages === "" ? null : Number(totalPages),
        rating: rating === "" ? null : Number(rating),
        notes: notes || null,
      });
    } catch (err) {
      setFormError(err.message || "Something went wrong");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <form className="card form" onSubmit={handleSubmit}>
      <div className="form-row">
        <label>
          Title
          <input value={title} onChange={(e) => setTitle(e.target.value)} disabled={submitting} />
          {errors.title && <span className="field-error">{errors.title}</span>}
        </label>
        <label>
          Author
          <input value={author} onChange={(e) => setAuthor(e.target.value)} disabled={submitting} />
          {errors.author && <span className="field-error">{errors.author}</span>}
        </label>
      </div>
      <div className="form-row">
        <label>
          Status
          <select value={status} onChange={(e) => setStatus(e.target.value)} disabled={submitting}>
            {STATUS_OPTIONS.map((s) => (
              <option key={s.value} value={s.value}>
                {s.label}
              </option>
            ))}
          </select>
        </label>
        <label>
          Total pages
          <input
            type="number"
            value={totalPages}
            onChange={(e) => setTotalPages(e.target.value)}
            disabled={submitting}
          />
          {errors.totalPages && <span className="field-error">{errors.totalPages}</span>}
        </label>
        <label>
          Rating (1-5)
          <input type="number" min="1" max="5" value={rating} onChange={(e) => setRating(e.target.value)} disabled={submitting} />
          {errors.rating && <span className="field-error">{errors.rating}</span>}
        </label>
      </div>
      <label>
        Notes
        <textarea value={notes} onChange={(e) => setNotes(e.target.value)} disabled={submitting} rows={2} />
      </label>
      {formError && <div className="field-error">{formError}</div>}
      <div className="form-actions">
        <button type="submit" className="btn btn-primary" disabled={submitting}>
          {submitting ? "Saving..." : "Save"}
        </button>
        {onCancel && (
          <button type="button" className="btn" onClick={onCancel} disabled={submitting}>
            Cancel
          </button>
        )}
      </div>
    </form>
  );
}
