from typing import Dict, List, Set
from fastapi import WebSocket


class ConnectionManager:
    """Tracks live sockets per authenticated user_id so events can be pushed
    only to the users who are entitled to see them (never a global broadcast).
    """

    def __init__(self):
        self.active: Dict[str, List[WebSocket]] = {}

    async def connect(self, user_id: str, websocket: WebSocket):
        await websocket.accept()
        self.active.setdefault(user_id, []).append(websocket)

    def disconnect(self, user_id: str, websocket: WebSocket):
        conns = self.active.get(user_id, [])
        if websocket in conns:
            conns.remove(websocket)
        if not conns and user_id in self.active:
            del self.active[user_id]

    async def send_to_user(self, user_id: str, event: dict):
        for ws in list(self.active.get(user_id, [])):
            try:
                await ws.send_json(event)
            except Exception:
                # Dead socket - drop it, client will reconnect and refresh state.
                self.disconnect(user_id, ws)

    async def send_to_users(self, user_ids: Set[str], event: dict):
        for uid in user_ids:
            await self.send_to_user(uid, event)


manager = ConnectionManager()
