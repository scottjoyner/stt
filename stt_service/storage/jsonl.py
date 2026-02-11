from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


class JsonlEventWriter:
    def __init__(self, root: Path, session_id: str) -> None:
        now = datetime.now(tz=timezone.utc)
        folder = root / "events" / f"{now.year:04d}" / f"{now.month:02d}" / f"{now.day:02d}"
        folder.mkdir(parents=True, exist_ok=True)
        self.path = folder / f"session_{session_id}.jsonl"

    def append(self, record: dict[str, Any]) -> None:
        with self.path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")
