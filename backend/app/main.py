import os
from dotenv import load_dotenv

load_dotenv()

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

from .database import Base, engine
from . import models  # noqa: F401  (ensures models are registered before create_all)
from .security import decode_access_token
from .ws_manager import manager
from .routers import auth, books, shelves, lending, activity, dashboard, catalog

Base.metadata.create_all(bind=engine)

app = FastAPI(title="BookNest API")

origins = [o.strip() for o in os.getenv("CORS_ORIGINS", "http://localhost:5173").split(",")]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(books.router)
app.include_router(shelves.router)
app.include_router(lending.router)
app.include_router(activity.router)
app.include_router(dashboard.router)
app.include_router(catalog.router)


@app.get("/health")
def health():
    return {"status": "ok"}


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket, token: str = ""):
    """The socket is authenticated with the same short-lived access token used
    for REST calls, passed as a query param since browsers can't attach
    custom headers to a WS handshake. A user is only ever registered under
    their own user_id in the connection manager, so `send_to_user` /
    `send_to_users` can never leak an event to someone it wasn't meant for -
    there is no global broadcast anywhere in this codebase."""
    user_id = decode_access_token(token)
    if not user_id:
        await websocket.close(code=4401)
        return

    await manager.connect(user_id, websocket)
    try:
        while True:
            # Clients don't need to send anything; we just need to detect
            # disconnects. Reading also lets a client send optional pings.
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(user_id, websocket)
    except Exception:
        manager.disconnect(user_id, websocket)
