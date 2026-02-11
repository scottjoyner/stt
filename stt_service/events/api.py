from __future__ import annotations

import asyncio

from fastapi import FastAPI, WebSocket, WebSocketDisconnect

from stt_service.api.routes_events import build_events_router
from stt_service.config import Settings
from stt_service.events.bus import EventBus
from stt_service.events.replay import EventReplayStore
from stt_service.runtime import RuntimePipeline


def build_app(settings: Settings, bus: EventBus, pipeline: RuntimePipeline | None = None) -> FastAPI:
    app = FastAPI(title="Realtime STT Service", version="0.2.0")
    replay = EventReplayStore(settings.data_dir / "events")

    @app.get("/health")
    async def health() -> dict[str, str]:
        return {"status": "ok", "service": "stt"}

    @app.get("/stats")
    async def stats() -> dict[str, object]:
        if pipeline is None:
            return {"status": "pipeline_not_running"}
        return pipeline.stats()

    @app.get("/config")
    async def config() -> dict[str, object]:
        return settings.model_dump()

    @app.post("/enroll")
    async def enroll() -> dict[str, str]:
        return {"message": "Use CLI: stt enroll --user <name>"}

    app.include_router(build_events_router(replay))

    @app.websocket("/ws/events")
    async def ws_events(websocket: WebSocket) -> None:
        await websocket.accept()
        queue = bus.subscribe("*")
        try:
            init = await asyncio.wait_for(websocket.receive_json(), timeout=1.0)
            if init.get("op") == "subscribe":
                from_event_id = init.get("from_event_id")
                for event in replay.from_event_id(from_event_id):
                    await websocket.send_json(event)
        except Exception:
            pass

        try:
            while True:
                event = await queue.get()
                await websocket.send_json(event.payload)
        except WebSocketDisconnect:
            return

    return app
