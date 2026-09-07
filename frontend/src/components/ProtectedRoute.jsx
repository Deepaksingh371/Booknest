import { Navigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext";
import Loading from "./Loading";

export default function ProtectedRoute({ children }) {
  const { user, initializing } = useAuth();
  if (initializing) return <Loading label="Restoring your session..." />;
  if (!user) return <Navigate to="/login" replace />;
  return children;
}
