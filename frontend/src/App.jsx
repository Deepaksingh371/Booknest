import { BrowserRouter, Routes, Route } from "react-router-dom";
import { AuthProvider } from "./context/AuthContext";
import ProtectedRoute from "./components/ProtectedRoute";
import NavBar from "./components/NavBar";
import LoginPage from "./pages/LoginPage";
import SignupPage from "./pages/SignupPage";
import DashboardPage from "./pages/DashboardPage";
import BooksPage from "./pages/BooksPage";
import BookPoolPage from "./pages/BookPoolPage";
import ShelvesPage from "./pages/ShelvesPage";
import ShelfDetailPage from "./pages/ShelfDetailPage";
import SharedWithMePage from "./pages/SharedWithMePage";
import BorrowedPage from "./pages/BorrowedPage";

export default function App() {
  return (
    <AuthProvider>
      <BrowserRouter>
        <NavBar />
        <main className="app-main">
          <Routes>
            <Route path="/login" element={<LoginPage />} />
            <Route path="/signup" element={<SignupPage />} />
            <Route
              path="/"
              element={
                <ProtectedRoute>
                  <DashboardPage />
                </ProtectedRoute>
              }
            />
            <Route
              path="/books"
              element={
                <ProtectedRoute>
                  <BooksPage />
                </ProtectedRoute>
              }
            />
            <Route
              path="/book-pool"
              element={
                <ProtectedRoute>
                  <BookPoolPage />
                </ProtectedRoute>
              }
            />
            <Route
              path="/shelves"
              element={
                <ProtectedRoute>
                  <ShelvesPage />
                </ProtectedRoute>
              }
            />
            <Route
              path="/shelves/:shelfId"
              element={
                <ProtectedRoute>
                  <ShelfDetailPage />
                </ProtectedRoute>
              }
            />
            <Route
              path="/shared-with-me"
              element={
                <ProtectedRoute>
                  <SharedWithMePage />
                </ProtectedRoute>
              }
            />
            <Route
              path="/borrowed"
              element={
                <ProtectedRoute>
                  <BorrowedPage />
                </ProtectedRoute>
              }
            />
          </Routes>
        </main>
      </BrowserRouter>
    </AuthProvider>
  );
}
