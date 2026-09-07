import { NavLink } from "react-router-dom";
import { useAuth } from "../context/AuthContext";

export default function NavBar() {
  const { user, logout, wsStatus } = useAuth();
  if (!user) return null;

  return (
    <header className="navbar">
      <div className="navbar-brand">📚 BookNest</div>
      <nav className="navbar-links">
        <NavLink to="/" end>
          Dashboard
        </NavLink>
        <NavLink to="/books">My Books</NavLink>
        <NavLink to="/book-pool">Book Pool</NavLink>
        <NavLink to="/shelves">My Shelves</NavLink>
        <NavLink to="/shared-with-me">Shared With Me</NavLink>
        <NavLink to="/borrowed">Borrowed</NavLink>
      </nav>
      <div className="navbar-right">
        <span
          className={`ws-dot ws-${wsStatus}`}
          title={wsStatus === "connected" ? "Live updates connected" : "Reconnecting..."}
        />
        <span className="navbar-user">{user.name}</span>
        <button type="button" className="btn btn-small" onClick={logout}>
          Log out
        </button>
      </div>
    </header>
  );
}
