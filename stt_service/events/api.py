from __future__ import annotations

import asyncio
from typing import AsyncIterator

from fastapi import FastAPI, WebSocket, WebSocketDisconnect

from stt_service.config import Settings
from stt_service.events.bus import EventBus


def build_app(settings: Settings, bus: EventBus) -> FastAPI:
    app = FastAPI(title="Realtime STT Service", version="0.1.0")

    @app.get("/health")
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/config")
    async def config() -> dict[str, object]:
        return settings.model_dump()

    @app.post("/enroll")
    async def enroll() -> dict[str, str]:
        return {"message": "Use CLI: stt enroll --user <name>"}

    @app.websocket("/ws/events")
    async def ws_events(websocket: WebSocket) -> None:
        await websocket.accept()
        queue = bus.subscribe("*")
        try:
            while True:
                event = await queue.get()
                await websocket.send_json({"type": event.type, "payload": event.payload})
        except WebSocketDisconnect:
            return

    return app
