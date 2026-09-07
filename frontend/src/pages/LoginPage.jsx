import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext";

export default function LoginPage() {
  const { login } = useAuth();
  const navigate = useNavigate();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [submitting, setSubmitting] = useState(false);

  async function handleSubmit(e) {
    e.preventDefault();
    setError("");
    setSubmitting(true);
    try {
      await login(email, password);
      navigate("/");
    } catch (err) {
      setError(err.message || "Login failed");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="auth-shell">
      <div className="auth-visual">
        <span className="auth-blob b1" />
        <span className="auth-blob b2" />
        <span className="auth-blob b3" />
        <div className="auth-visual-content">
          <div className="auth-brand">📚 BookNest</div>
          <h2 className="auth-tagline">Your reading life, all in one shelf.</h2>
          <p className="auth-subtagline">
            Track progress, share shelves with friends, lend books, and discover
            something new from the pool - all in one place.
          </p>
        </div>
        <div>
          <div className="auth-floating-shelf">
            <span style={{ height: 70, background: "#ffe1c2" }} />
            <span style={{ height: 90 }} />
            <span style={{ height: 60, background: "#d9c2ff" }} />
            <span style={{ height: 80, background: "#ffe1c2" }} />
            <span style={{ height: 50 }} />
          </div>
          <p className="auth-quote">"A room without books is like a body without a soul."</p>
        </div>
      </div>

      <div className="auth-form-side">
        <form className="auth-card" onSubmit={handleSubmit}>
          <h1>Welcome back</h1>
          <p className="muted">Log in to your account</p>
          <label>
            Email
            <input
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              disabled={submitting}
              required
            />
          </label>
          <label>
            Password
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              disabled={submitting}
              required
            />
          </label>
          {error && <div className="field-error">{error}</div>}
          <button type="submit" className="btn btn-primary" disabled={submitting}>
            {submitting ? "Logging in..." : "Log in"}
          </button>
          <p className="muted small">
            No account? <Link to="/signup">Sign up</Link>
          </p>
        </form>
      </div>
    </div>
  );
}
