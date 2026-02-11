from __future__ import annotations

import json
from pathlib import Path
from typing import Any


class EventReplayStore:
    def __init__(self, root: Path) -> None:
        self.root = root
        self.root.mkdir(parents=True, exist_ok=True)
        self.index_path = self.root / "events_index.json"
        if not self.index_path.exists():
            self.index_path.write_text(json.dumps({"items": []}))

    def add_index(self, event_id: str, path: Path, line_no: int, ts_wall: str) -> None:
        payload = json.loads(self.index_path.read_text())
        items = payload.get("items", [])
        items.append({"event_id": event_id, "path": str(path), "line_no": line_no, "ts_wall": ts_wall, "cursor": f"{path}:{line_no}"})
        payload["items"] = items[-5000:]
        self.index_path.write_text(json.dumps(payload))

    def _load_event_by_ref(self, item: dict[str, Any]) -> dict[str, Any] | None:
        path = Path(item["path"])
        if not path.exists():
            return None
        with path.open("r", encoding="utf-8") as f:
            for idx, line in enumerate(f, start=1):
                if idx == int(item["line_no"]):
                    return json.loads(line)
        return None

    def recent(self, seconds: int) -> list[dict[str, Any]]:
        payload = json.loads(self.index_path.read_text())
        items = payload.get("items", [])
        refs = items[-200:] if seconds <= 0 else items[-2000:]
        out: list[dict[str, Any]] = []
        for ref in refs:
            ev = self._load_event_by_ref(ref)
            if ev:
                ev["cursor"] = ref.get("cursor")
                out.append(ev)
        return out

    def from_event_id(self, event_id: str | None, limit: int = 500) -> list[dict[str, Any]]:
        return self.from_cursor(from_event_id=event_id, from_line=None, limit=limit)

    def from_cursor(self, from_event_id: str | None = None, from_line: int | None = None, limit: int = 500) -> list[dict[str, Any]]:
        payload = json.loads(self.index_path.read_text())
        items = payload.get("items", [])
        start = 0
        if from_line is not None:
            for idx, item in enumerate(items):
                if int(item.get("line_no", 0)) >= int(from_line):
                    start = idx
                    break
        elif from_event_id:
            for idx, item in enumerate(items):
                if item.get("event_id") == from_event_id:
                    start = idx + 1
                    break
        refs = items[start : start + limit]
        out: list[dict[str, Any]] = []
        for ref in refs:
            ev = self._load_event_by_ref(ref)
            if ev:
                ev["cursor"] = ref.get("cursor")
                out.append(ev)
        return out
