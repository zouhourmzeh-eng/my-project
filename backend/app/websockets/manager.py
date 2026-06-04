import json
from collections import defaultdict
from typing import Any

from fastapi import WebSocket


class ConnectionManager:
    """In-memory pub/sub for WebSocket clients.

    Suitable for single-instance deployments. For multi-instance,
    swap in Redis pub/sub.
    """

    def __init__(self) -> None:
        self._rooms: dict[str, set[WebSocket]] = defaultdict(set)
        self._users: dict[int, set[WebSocket]] = defaultdict(set)

    async def join_room(self, room: str, ws: WebSocket) -> None:
        await ws.accept()
        self._rooms[room].add(ws)

    async def join_user(self, user_id: int, ws: WebSocket) -> None:
        await ws.accept()
        self._users[user_id].add(ws)

    def leave_room(self, room: str, ws: WebSocket) -> None:
        self._rooms.get(room, set()).discard(ws)

    def leave_user(self, user_id: int, ws: WebSocket) -> None:
        self._users.get(user_id, set()).discard(ws)

    async def broadcast_room(self, room: str, payload: dict[str, Any]) -> None:
        data = json.dumps(payload, default=str)
        dead: list[WebSocket] = []
        for ws in list(self._rooms.get(room, set())):
            try:
                await ws.send_text(data)
            except Exception:
                dead.append(ws)
        for ws in dead:
            self._rooms[room].discard(ws)

    async def notify_user(self, user_id: int, payload: dict[str, Any]) -> None:
        data = json.dumps(payload, default=str)
        dead: list[WebSocket] = []
        for ws in list(self._users.get(user_id, set())):
            try:
                await ws.send_text(data)
            except Exception:
                dead.append(ws)
        for ws in dead:
            self._users[user_id].discard(ws)


manager = ConnectionManager()
