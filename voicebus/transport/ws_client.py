from __future__ import annotations

from collections.abc import AsyncIterator

import websockets


class VoicebusWsClient:
    def __init__(self, url: str, from_event_id: str | None = None) -> None:
        self.url = url
        self.from_event_id = from_event_id

    async def events(self) -> AsyncIterator[dict]:
        async with websockets.connect(self.url) as ws:
            await ws.send(
                '{"op":"subscribe","schema_version":"3.0","from_event_id":%s}'
                % (f'"{self.from_event_id}"' if self.from_event_id else "null")
            )
            async for msg in ws:
                yield __import__("json").loads(msg)
