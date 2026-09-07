# BookNest

A reading-tracker app: manage your books, organize them into shelves, share
shelves with other users under owner/editor/viewer roles, log reading
progress, and lend books to other users on the platform — with live,
per-user real-time updates over WebSockets.

## Stack

- **Backend:** Python + FastAPI + SQLAlchemy
- **Database:** SQLite by default (see "Why SQLite" below); the models use
  only standard SQL types, so pointing `DATABASE_URL` at Postgres works with
  no code changes.
- **Frontend:** React (Vite), plain CSS, `react-router-dom`
- **Auth:** JWT access tokens + rotating refresh tokens
- **Real-time:** native WebSockets (FastAPI's built-in support, no separate
  library) — no polling anywhere in the app

### Why SQLite (and why that's a reasonable default here)

The brief allows SQLite "if you justify it." I used it as the default so the
seed script and app run with zero external setup on a clean clone (no Docker,
no local Postgres install, nothing to configure) — that matters for a
reviewer doing a fast clean-clone test. It's not a workaround for the
relational modeling: every relationship (many-to-many shelves/books, shelf
shares, lending) is expressed with real foreign keys and a real join table,
and `DATABASE_URL=postgresql+psycopg2://...` in `.env` is the only change
needed to run this against Postgres instead — the SQLAlchemy models don't use
any SQLite-specific features.

## How to run (clean clone)

### Backend

```bash
cd backend
python3 -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
python seed.py                  # creates the SQLite DB + demo data
uvicorn app.main:app --reload --port 8000
```

The API is now at `http://localhost:8000` (interactive docs at `/docs`).

### Frontend

```bash
cd frontend
npm install
cp .env.example .env
npm run dev
```

The app is now at `http://localhost:5173`.

### Demo accounts (created by `seed.py`, password for all: `Password123`)

| Email | Role in the demo |
|---|---|
| `alice@example.com` | Owns "Sci-Fi Favorites" shelf, lent *The Hobbit* to Bob |
| `bob@example.com` | Editor on Alice's shelf, currently borrowing *The Hobbit* |
| `carol@example.com` | Viewer on Alice's shelf |

To see the live-update and RBAC flows: log in as Alice in one browser window
and Bob (or Carol) in another.

## Book Pool

A shared, curated catalog (`CatalogBook`) any logged-in user can browse
(search + genre filter + pagination) from **Book Pool** in the nav. Adding a
title creates an independent copy in that user's own library (`Book` row,
status `want_to_read`) — the catalog entry itself is never owned by anyone
and isn't affected by what individual users do with their copy. Adding the
same title twice is rejected (`400`), and it immediately shows up in that
user's dashboard counts and activity feed, same as any other book add.

## Data model

```
User
 ├─< Book (owner_id)                       one owner, many books
 ├─< Shelf (owner_id)                      one owner, many shelves
 ├─< ShelfShare (user_id)                  a user's role on shelves they don't own
 └─< ActivityLog (user_id)                 per-user activity feed

Shelf ─┬─< ShelfBook >─┬─ Book             many-to-many join table
       └─< ShelfShare                      one row per (shelf, collaborator, role)

Book ─┬─< ShelfBook                        a book can be on many shelves
      └── Lending (nullable, 1:1)          at most one *active* lending per book

Lending: book_id (unique while active), owner_id, borrower_id, lent_at, returned_at
```

- **Shelves and books** are many-to-many through `ShelfBook`. Deleting a
  shelf deletes only its `ShelfBook` rows and `ShelfShare` rows (cascade) —
  never the books. Deleting a book cascades its `ShelfBook` rows so it's
  cleanly removed from every shelf, with no orphaned references.
- **Roles** are stored per (shelf, user) in `ShelfShare`. The owner isn't a
  row in that table — it's `Shelf.owner_id` — so "only the owner can
  share/delete/change roles" is a simple identity check, not a role
  comparison that could be spoofed by writing an `owner` row.
- **Lending** is its own table rather than fields on `Book`, so "a book can
  only be lent to one person at a time" is enforced by checking for an
  existing row with `returned_at IS NULL`, and the full lending history
  isn't destroyed by a return (it's a "closed" row, not a delete).

## Refresh-token flow

- **Access token** (15 min): a signed JWT returned in the JSON response body
  and held only in memory in the React app (`api.js`). It's attached as an
  `Authorization: Bearer` header on every request. It is never persisted to
  `localStorage` — that would be readable by any injected script (XSS), so
  keeping it in memory limits the blast radius to the current tab/session.
- **Refresh token** (7 days): a signed JWT set as an **httpOnly, SameSite=Lax**
  cookie scoped to `/auth`. Because it's httpOnly, client-side JS (and thus
  an XSS payload) can never read it. It's also stored **hashed** (SHA-256)
  server-side in a `refresh_tokens` table, purely for revocation — the raw
  token itself is never stored anywhere.
- **On expiry:** `api.js` wraps every request; a `401` triggers exactly one
  call to `POST /auth/refresh` (concurrent 401s share the same in-flight
  refresh promise so they don't race), which reads the cookie, validates and
  **rotates** it — the old refresh token is marked `revoked` and a brand new
  access/refresh pair is issued — then the original request is retried
  transparently. If refresh itself fails (expired/revoked), the user is
  logged out client-side.
- Rotation means a stolen refresh token is only useful once before the
  legitimate client's next refresh invalidates it, which makes reuse
  detectable in principle (this project doesn't add reuse-detection
  alerting, see "known issues" below).

## Enforcing shelf roles (owner / editor / viewer) on the backend

Every shelf-scoped endpoint resolves the caller's role itself — it never
trusts anything from the client:

- `owner_id` on `Shelf` is checked directly for owner-only actions (share,
  change a role, remove a collaborator, delete the shelf). A non-owner
  calling any of these gets `403` before anything else executes.
- For "add/remove book on a shelf," the backend looks up the caller's row in
  `ShelfShare` (or confirms they're the owner) and rejects `viewer` with
  `403` — this check happens in the route handler itself, so there's no way
  to reach the mutation by skipping a disabled button; calling the API
  directly with a viewer's token is rejected the same way the UI is.
- Editors can only add books **they themselves own** to a shared shelf (the
  book's `owner_id` must match the caller) — an editor can't inject someone
  else's private book onto the shelf just because they have edit rights on
  the shelf.

## WebSocket design

- **Auth:** the socket is opened at `/ws?token=<access_token>` using the same
  short-lived JWT as REST calls (browsers can't set custom headers during
  the WS handshake, so it travels as a query param instead of a header). The
  server decodes it before accepting the connection and closes immediately
  (code `4401`) if it's missing or invalid.
- **Scoping:** `ConnectionManager` (`ws_manager.py`) keeps a dict of
  `user_id -> [live sockets]`. Every event is sent with `send_to_user` /
  `send_to_users` against an explicit set of user IDs computed server-side
  (e.g. a shelf's owner + its `ShelfShare` rows) — there is no broadcast
  method in the codebase that sends to "everyone," so a viewer with no
  access to a shelf is structurally incapable of receiving its events; they
  were never in the recipient set to begin with.
- **What's pushed:** every `activity`-producing action (book added/removed
  from a shelf, lending/return, shelf shared, role changed, collaborator
  removed) computes its recipient set and pushes an `{type: "activity", ...}`
  frame to each of them, and also writes a persisted `ActivityLog` row per
  recipient so a refresh shows the same state a live push would have.
- **Disconnects/reconnects:** the frontend (`ws.js`) reconnects with capped
  exponential backoff (1s → 2s → 4s ... up to 15s) whenever the socket
  closes unexpectedly. While disconnected, the app keeps working off its
  last-fetched state (nothing blocks on the socket), and a manual refresh
  always re-fetches current truth from the REST API regardless of socket
  state — the socket is purely an optimization for immediacy, never a
  source of truth.

## What was hard

- **Getting lending's uniqueness right** without a separate "is this book
  lent" boolean living out of sync with reality — modeling lending as its
  own table with `returned_at IS NULL` meaning "active" turned out cleaner
  than a flag on `Book`, and it keeps history for free.
- **Deciding what a viewer's activity feed should contain.** The spec wants
  events "for shelves shared with them" delivered live; I resolved this by
  computing the recipient set at write-time and writing one `ActivityLog`
  row per recipient (rather than one row + a fan-out at read-time), which
  keeps the live push and the persisted "what would I see on refresh" feed
  guaranteed to agree.
- **Refresh-token rotation edge cases** — making sure two tabs refreshing at
  nearly the same moment don't each invalidate the other's brand-new token
  (handled by rotating server-side per request and having the frontend
  de-duplicate concurrent refresh calls into one in-flight promise).

## Known issues / incomplete

- No reuse-detection alerting on refresh tokens (a rotated/revoked token
  being presented again is rejected, but doesn't yet trigger revoking the
  rest of that user's sessions).
- No automated test suite included (see stretch goals — this was deprioritized
  in favor of getting full core-scope coverage solid).
- The dashboard's "shelf with the most books" doesn't break ties
  deterministically beyond insertion order.
- No CSV import, no Docker Compose, no live deploy — see stretch goals.

## What I'd improve with more time

- Add refresh-token reuse detection (revoke all sessions for a user if a
  used/expired refresh token is presented again).
- Add an automated test suite for auth, lending rules, and RBAC — these are
  the highest-value paths to lock down with tests given how easy it'd be to
  regress a permission check while refactoring.
- Move activity fan-out and WebSocket delivery onto a small task queue so a
  slow socket write can't add latency to the request that triggered it.
- Dockerize the whole stack for one-command startup.

## Where AI was used

I used AI assistance to scaffold this project end-to-end — the FastAPI
backend (models, routers, JWT/refresh-token flow, WebSocket manager) and the
React frontend (pages, API client with transparent refresh, WebSocket hook).
I tested the backend directly against a running server (auth, RBAC rejection
paths, lending conflicts, progress validation, token refresh) rather than
just trusting generated code, and read through the security-sensitive parts
(password hashing, token storage/rotation, role checks, WebSocket scoping)
closely since those are exactly the parts a reviewer would want explained
and are also the parts most damaging to get subtly wrong. The biggest thing
I'd flag for follow-up discussion is the refresh-token rotation logic in
`backend/app/routers/auth.py` — that's the piece with the most moving parts
and the most worth walking through line by line.
