import { createContext, useContext, useEffect, useRef, useState, useCallback } from "react";
import { api, setAccessToken, getAccessToken, setOnUnauthorized } from "../api";
import { connectSocket } from "../ws";

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [initializing, setInitializing] = useState(true);
  const [wsStatus, setWsStatus] = useState("disconnected");
  const listenersRef = useRef(new Set());

  const subscribeToEvents = useCallback((fn) => {
    listenersRef.current.add(fn);
    return () => listenersRef.current.delete(fn);
  }, []);

  const handleEvent = useCallback((event) => {
    listenersRef.current.forEach((fn) => fn(event));
  }, []);

  useEffect(() => {
    setOnUnauthorized(() => setUser(null));
    // Try to restore a session from the httpOnly refresh cookie on first load.
    api
      .refresh()
      .then(() => api.me())
      .then(setUser)
      .catch(() => setUser(null))
      .finally(() => setInitializing(false));
  }, []);

  useEffect(() => {
    if (!user) return undefined;
    const cleanup = connectSocket(getAccessToken(), handleEvent, setWsStatus);
    return cleanup;
    // Reconnect whenever the user (and thus a fresh access token) changes.
  }, [user, handleEvent]);

  async function login(email, password) {
    const data = await api.login({ email, password });
    setAccessToken(data.access_token);
    setUser(data.user);
  }

  async function signup(name, email, password) {
    const data = await api.signup({ name, email, password });
    setAccessToken(data.access_token);
    setUser(data.user);
  }

  async function logout() {
    try {
      await api.logout();
    } catch {
      // best-effort
    }
    setAccessToken(null);
    setUser(null);
  }

  return (
    <AuthContext.Provider
      value={{ user, initializing, login, signup, logout, subscribeToEvents, wsStatus }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  return useContext(AuthContext);
}
