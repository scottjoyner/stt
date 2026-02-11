from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from stt_service.events.replay import EventReplayStore
from stt_service.events.schema import validate_event


class JsonlEventWriter:
    def __init__(self, root: Path, session_id: str) -> None:
        now = datetime.now(tz=timezone.utc)
        folder = root / "events" / f"{now.year:04d}" / f"{now.month:02d}" / f"{now.day:02d}"
        folder.mkdir(parents=True, exist_ok=True)
        self.path = folder / f"session_{session_id}.jsonl"
        self.replay = EventReplayStore(root / "events")
        self._line_no = self._count_lines()

    def _count_lines(self) -> int:
        if not self.path.exists():
            return 0
        with self.path.open("r", encoding="utf-8") as f:
            return sum(1 for _ in f)

    def append(self, record: dict[str, Any]) -> dict[str, Any]:
        validated = validate_event(record)
        with self.path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(validated, ensure_ascii=False) + "\n")
        self._line_no += 1
        self.replay.add_index(validated["event_id"], self.path, self._line_no, validated["ts_wall"])
        return validated
