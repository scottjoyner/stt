from __future__ import annotations

from fastapi import APIRouter, Query

from stt_service.events.replay import EventReplayStore


def build_events_router(replay: EventReplayStore) -> APIRouter:
    router = APIRouter()

    @router.get("/events/recent")
    async def events_recent(seconds: int = Query(default=60, ge=0, le=3600), limit: int = Query(default=200, ge=1, le=5000)) -> dict[str, object]:
        return {"events": replay.recent(seconds)[-limit:]}

    return router
