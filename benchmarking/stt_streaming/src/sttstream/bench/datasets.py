from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path


@dataclass
class DatasetItem:
    audio_path: Path
    text: str
    id: str
    text_path: Path | None = None


def load_manifest(path: Path) -> list[DatasetItem]:
    items: list[DatasetItem] = []
    with path.open() as fh:
        for line in fh:
            row = json.loads(line)
            text = row.get("text", "")
            text_path = Path(row["text_path"]) if row.get("text_path") else None
            if text_path and text_path.exists():
                text = text_path.read_text()
            items.append(DatasetItem(audio_path=Path(row["audio_path"]), text=text, id=row["id"], text_path=text_path))
    return items
