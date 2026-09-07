export default function ErrorMessage({ message, onRetry }) {
  if (!message) return null;
  return (
    <div className="state state-error">
      <span>{message}</span>
      {onRetry && (
        <button type="button" className="btn btn-small" onClick={onRetry}>
          Retry
        </button>
      )}
    </div>
  );
}
