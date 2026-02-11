from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

import numpy as np

from stt_service.utils.time import now_wall_iso


@dataclass(slots=True)
class Voiceprint:
    user: str
    embedding: np.ndarray
    sample_count: int
    model_version: str
    created_at: str

    def to_json(self) -> dict:
        return {
            "user": self.user,
            "embedding": self.embedding.tolist(),
            "sample_count": self.sample_count,
            "embedding_dims": int(self.embedding.shape[0]),
            "model_version": self.model_version,
            "created_at": self.created_at,
        }


class VoiceprintStore:
    def __init__(self, root: Path) -> None:
        self.root = root
        self.root.mkdir(parents=True, exist_ok=True)

    def save(self, vp: Voiceprint) -> Path:
        path = self.root / f"{vp.user}.json"
        path.write_text(json.dumps(vp.to_json(), indent=2))
        return path

    def load_all(self) -> list[Voiceprint]:
        out: list[Voiceprint] = []
        for path in sorted(self.root.glob("*.json")):
            raw = json.loads(path.read_text())
            out.append(
                Voiceprint(
                    user=raw["user"],
                    embedding=np.array(raw["embedding"], dtype=np.float32),
                    sample_count=int(raw.get("sample_count", 0)),
                    model_version=raw.get("model_version", "unknown"),
                    created_at=raw.get("created_at", now_wall_iso()),
                )
            )
        return out
