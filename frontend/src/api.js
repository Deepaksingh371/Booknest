const API_URL = import.meta.env.VITE_API_URL || "http://localhost:8000";

let accessToken = null;
let onUnauthorized = () => {};

// A single in-flight refresh promise so concurrent 401s don't all race to
// refresh at once (which would revoke each other's rotated token).
let refreshPromise = null;

export function setAccessToken(token) {
  accessToken = token;
}

export function getAccessToken() {
  return accessToken;
}

export function setOnUnauthorized(fn) {
  onUnauthorized = fn;
}

async function doRefresh() {
  if (!refreshPromise) {
    refreshPromise = fetch(`${API_URL}/auth/refresh`, {
      method: "POST",
      credentials: "include",
    })
      .then(async (res) => {
        if (!res.ok) throw new Error("refresh_failed");
        const data = await res.json();
        accessToken = data.access_token;
        return data;
      })
      .finally(() => {
        refreshPromise = null;
      });
  }
  return refreshPromise;
}

class ApiError extends Error {
  constructor(message, status, details) {
    super(message);
    this.status = status;
    this.details = details;
  }
}

export async function apiFetch(path, options = {}, _isRetry = false) {
  const headers = { "Content-Type": "application/json", ...(options.headers || {}) };
  if (accessToken) headers["Authorization"] = `Bearer ${accessToken}`;

  const res = await fetch(`${API_URL}${path}`, {
    ...options,
    headers,
    credentials: "include",
  });

  if (res.status === 401 && !_isRetry && path !== "/auth/refresh" && path !== "/auth/login") {
    try {
      await doRefresh();
      return apiFetch(path, options, true);
    } catch {
      accessToken = null;
      onUnauthorized();
      throw new ApiError("Session expired. Please log in again.", 401);
    }
  }

  if (!res.ok) {
    let detail = res.statusText;
    try {
      const body = await res.json();
      detail = body.detail || detail;
    } catch {
      // no JSON body
    }
    throw new ApiError(Array.isArray(detail) ? detail.map((d) => d.msg).join(", ") : detail, res.status, detail);
  }

  if (res.status === 204) return null;
  return res.json();
}

export const api = {
  signup: (data) => apiFetch("/auth/signup", { method: "POST", body: JSON.stringify(data) }),
  login: (data) => apiFetch("/auth/login", { method: "POST", body: JSON.stringify(data) }),
  logout: () => apiFetch("/auth/logout", { method: "POST" }),
  me: () => apiFetch("/auth/me"),
  refresh: doRefresh,

  listBooks: (params) => apiFetch(`/books?${new URLSearchParams(params).toString()}`),
  createBook: (data) => apiFetch("/books", { method: "POST", body: JSON.stringify(data) }),
  updateBook: (id, data) => apiFetch(`/books/${id}`, { method: "PATCH", body: JSON.stringify(data) }),
  deleteBook: (id) => apiFetch(`/books/${id}`, { method: "DELETE" }),
  logProgress: (id, current_page) =>
    apiFetch(`/books/${id}/progress`, { method: "POST", body: JSON.stringify({ current_page }) }),
  lendBook: (id, borrower_email) =>
    apiFetch(`/books/${id}/lend`, { method: "POST", body: JSON.stringify({ borrower_email }) }),
  returnBook: (id) => apiFetch(`/books/${id}/return`, { method: "POST" }),
  borrowed: () => apiFetch("/borrowed"),

  listShelves: () => apiFetch("/shelves"),
  sharedWithMe: () => apiFetch("/shelves/shared-with-me"),
  createShelf: (name) => apiFetch("/shelves", { method: "POST", body: JSON.stringify({ name }) }),
  deleteShelf: (id) => apiFetch(`/shelves/${id}`, { method: "DELETE" }),
  shelfBooks: (id) => apiFetch(`/shelves/${id}/books`),
  addBookToShelf: (shelfId, bookId) => apiFetch(`/shelves/${shelfId}/books/${bookId}`, { method: "POST" }),
  removeBookFromShelf: (shelfId, bookId) => apiFetch(`/shelves/${shelfId}/books/${bookId}`, { method: "DELETE" }),
  collaborators: (id) => apiFetch(`/shelves/${id}/collaborators`),
  shareShelf: (id, email, role) =>
    apiFetch(`/shelves/${id}/share`, { method: "POST", body: JSON.stringify({ email, role }) }),
  updateRole: (shelfId, userId, role) =>
    apiFetch(`/shelves/${shelfId}/collaborators/${userId}`, { method: "PATCH", body: JSON.stringify({ role }) }),
  removeCollaborator: (shelfId, userId) =>
    apiFetch(`/shelves/${shelfId}/collaborators/${userId}`, { method: "DELETE" }),

  browseCatalog: (params) => apiFetch(`/catalog?${new URLSearchParams(params).toString()}`),
  addFromCatalog: (catalogId) => apiFetch(`/catalog/${catalogId}/add`, { method: "POST" }),

  activity: () => apiFetch("/activity"),
  dashboard: () => apiFetch("/dashboard"),
};

export { ApiError, API_URL };
