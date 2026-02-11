from __future__ import annotations

import asyncio
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class Event:
    type: str
    payload: dict[str, Any]


@dataclass
class EventBus:
    _subscribers: dict[str, list[asyncio.Queue[Event]]] = field(default_factory=lambda: defaultdict(list))

    def subscribe(self, event_type: str, maxsize: int = 100) -> asyncio.Queue[Event]:
        queue: asyncio.Queue[Event] = asyncio.Queue(maxsize=maxsize)
        self._subscribers[event_type].append(queue)
        return queue

    async def publish(self, event_type: str, payload: dict[str, Any]) -> None:
        event = Event(type=event_type, payload=payload)
        targets = self._subscribers.get(event_type, []) + self._subscribers.get("*", [])
        for queue in targets:
            if queue.full():
                _ = queue.get_nowait()
            await queue.put(event)
