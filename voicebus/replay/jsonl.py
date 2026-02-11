from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Iterator


class JsonlReplay:
    def __init__(self, path: Path) -> None:
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def write(self, event: dict[str, Any]) -> int:
        line_no = self._count_lines() + 1
        with self.path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(event, ensure_ascii=False) + "\n")
        return line_no

    def read(self, from_line: int = 1) -> Iterator[dict[str, Any]]:
        if not self.path.exists():
            return iter(())
        with self.path.open("r", encoding="utf-8") as f:
            for idx, line in enumerate(f, start=1):
                if idx < from_line:
                    continue
                yield json.loads(line)

    def _count_lines(self) -> int:
        if not self.path.exists():
            return 0
        with self.path.open("r", encoding="utf-8") as f:
            return sum(1 for _ in f)
