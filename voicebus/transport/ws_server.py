from __future__ import annotations

from fastapi import APIRouter, WebSocket, WebSocketDisconnect


class WsHub:
    def __init__(self) -> None:
        self._clients: set[WebSocket] = set()

    async def broadcast(self, payload: dict) -> None:
        stale: list[WebSocket] = []
        for ws in self._clients:
            try:
                await ws.send_json(payload)
            except Exception:
                stale.append(ws)
        for ws in stale:
            self._clients.discard(ws)

    def router(self) -> APIRouter:
        router = APIRouter()

        @router.websocket("/ws/events")
        async def ws_events(websocket: WebSocket) -> None:
            await websocket.accept()
            self._clients.add(websocket)
            try:
                while True:
                    await websocket.receive_text()
            except WebSocketDisconnect:
                self._clients.discard(websocket)

        return router
