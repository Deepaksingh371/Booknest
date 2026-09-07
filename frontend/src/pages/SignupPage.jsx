import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext";

export default function SignupPage() {
  const { signup } = useAuth();
  const navigate = useNavigate();
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [submitting, setSubmitting] = useState(false);

  async function handleSubmit(e) {
    e.preventDefault();
    setError("");
    setSubmitting(true);
    try {
      await signup(name, email, password);
      navigate("/");
    } catch (err) {
      setError(err.message || "Signup failed");
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
          <h2 className="auth-tagline">Start building your shelf today.</h2>
          <p className="auth-subtagline">
            Pull from a shared book pool, invite friends to your shelves, and
            never lose track of who borrowed what again.
          </p>
        </div>
        <div>
          <div className="auth-floating-shelf">
            <span style={{ height: 60, background: "#d9c2ff" }} />
            <span style={{ height: 80, background: "#ffe1c2" }} />
            <span style={{ height: 50 }} />
            <span style={{ height: 90 }} />
            <span style={{ height: 70, background: "#ffe1c2" }} />
          </div>
          <p className="auth-quote">"So many books, so little time." - Frank Zappa</p>
        </div>
      </div>

      <div className="auth-form-side">
        <form className="auth-card" onSubmit={handleSubmit}>
          <h1>Create your account</h1>
          <p className="muted">Join BookNest in seconds</p>
          <label>
            Name
            <input value={name} onChange={(e) => setName(e.target.value)} disabled={submitting} required />
          </label>
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
            <span className="hint">At least 8 characters, one uppercase letter, one digit.</span>
          </label>
          {error && <div className="field-error">{error}</div>}
          <button type="submit" className="btn btn-primary" disabled={submitting}>
            {submitting ? "Creating account..." : "Sign up"}
          </button>
          <p className="muted small">
            Already have an account? <Link to="/login">Log in</Link>
          </p>
        </form>
      </div>
    </div>
  );
}
