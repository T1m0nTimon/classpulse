"""WebSocket hub. Messages are tiny "something changed" events; clients re-fetch via REST.

Participant sockets carry no identity at all; we only count them.
shortcut: in-process hub, run a single worker (uvicorn default); for multi-worker use Redis pub/sub.
"""

import asyncio
import json
from collections import defaultdict

from fastapi import WebSocket


class Hub:
    def __init__(self):
        self.rooms: dict[str, set[WebSocket]] = defaultdict(set)

    async def join(self, room: str, ws: WebSocket):
        self.rooms[room].add(ws)

    def leave(self, room: str, ws: WebSocket):
        self.rooms[room].discard(ws)
        if not self.rooms[room]:
            self.rooms.pop(room, None)

    def count(self, room: str) -> int:
        return len(self.rooms.get(room, ()))

    async def send(self, room: str, event: dict):
        data = json.dumps(event)
        sockets = list(self.rooms.get(room, ()))

        async def _one(ws):
            try:
                await asyncio.wait_for(ws.send_text(data), timeout=5)
            except Exception:  # noqa: BLE001 - dead socket, drop it
                self.leave(room, ws)

        await asyncio.gather(*(_one(ws) for ws in sockets))

    async def notify(self, session_id: str, event: dict, students: bool = True):
        await self.send(f"t:{session_id}", event)
        if students:
            await self.send(f"p:{session_id}", event)

    async def participants_changed(self, session_id: str):
        await self.send(f"t:{session_id}", {"type": "participants", "count": self.count(f"p:{session_id}")})


hub = Hub()
