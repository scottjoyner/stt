from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class Settings:
    sample_rate: int = 16_000
    channels: int = 1
    frame_ms: int = 20
    ring_buffer_seconds: int = 10

    vad_mode: str = "energy"
    vad_energy_threshold: float = 0.015
    vad_silence_ms: int = 900
    vad_min_speech_ms: int = 350
    vad_preroll_ms: int = 300

    stt_model: str = "base"
    stt_chunk_ms: int = 700

    trigger_phrases: list[str] = field(default_factory=lambda: ["hey assistant", "computer", "ok ralph"])
    trigger_enabled: bool = True

    auth_threshold: float = 0.55
    speaker_model: str = "speechbrain/spkrec-ecapa-voxceleb"

    data_dir: Path = Path("data")
    save_segment_wav: bool = False

    queue_maxsize: int = 100
    session_id: str = "local"

    def __init__(self, **kwargs: Any) -> None:
        env = {
            "sample_rate": os.getenv("STT_SAMPLE_RATE"),
            "vad_mode": os.getenv("VAD_MODE"),
            "vad_silence_ms": os.getenv("VAD_SILENCE_MS"),
            "stt_model": os.getenv("STT_MODEL"),
            "auth_threshold": os.getenv("AUTH_THRESHOLD"),
            "data_dir": os.getenv("DATA_DIR"),
        }
        alias_map = {
            "STT_SAMPLE_RATE": "sample_rate",
            "VAD_MODE": "vad_mode",
            "VAD_SILENCE_MS": "vad_silence_ms",
            "STT_MODEL": "stt_model",
            "AUTH_THRESHOLD": "auth_threshold",
            "DATA_DIR": "data_dir",
        }
        merged = {k: v for k, v in env.items() if v is not None}
        for k, v in kwargs.items():
            merged[alias_map.get(k, k)] = v

        # defaults
        self.sample_rate = int(merged.get("sample_rate", 16_000))
        self.channels = int(merged.get("channels", 1))
        self.frame_ms = int(merged.get("frame_ms", 20))
        self.ring_buffer_seconds = int(merged.get("ring_buffer_seconds", 10))
        self.vad_mode = str(merged.get("vad_mode", "energy"))
        self.vad_energy_threshold = float(merged.get("vad_energy_threshold", 0.015))
        self.vad_silence_ms = int(merged.get("vad_silence_ms", 900))
        self.vad_min_speech_ms = int(merged.get("vad_min_speech_ms", 350))
        self.vad_preroll_ms = int(merged.get("vad_preroll_ms", 300))
        self.stt_model = str(merged.get("stt_model", "base"))
        self.stt_chunk_ms = int(merged.get("stt_chunk_ms", 700))
        self.trigger_phrases = list(merged.get("trigger_phrases", ["hey assistant", "computer", "ok ralph"]))
        self.trigger_enabled = bool(merged.get("trigger_enabled", True))
        self.auth_threshold = float(merged.get("auth_threshold", 0.55))
        self.speaker_model = str(merged.get("speaker_model", "speechbrain/spkrec-ecapa-voxceleb"))
        self.data_dir = Path(merged.get("data_dir", "data"))
        self.save_segment_wav = bool(merged.get("save_segment_wav", False))
        self.queue_maxsize = int(merged.get("queue_maxsize", 100))
        self.session_id = str(merged.get("session_id", "local"))

    @classmethod
    def from_file(cls, path: Path | None) -> "Settings":
        if path is None or not path.exists():
            return cls()
        if path.suffix.lower() in {".yaml", ".yml"}:
            try:
                import yaml
            except Exception:
                raise RuntimeError("PyYAML is required for yaml config")
            payload = yaml.safe_load(path.read_text()) or {}
        elif path.suffix.lower() == ".json":
            payload = json.loads(path.read_text())
        else:
            raise ValueError(f"Unsupported config file: {path}")
        return cls(**payload)

    def model_dump(self) -> dict[str, Any]:
        return {
            "sample_rate": self.sample_rate,
            "channels": self.channels,
            "frame_ms": self.frame_ms,
            "ring_buffer_seconds": self.ring_buffer_seconds,
            "vad_mode": self.vad_mode,
            "vad_energy_threshold": self.vad_energy_threshold,
            "vad_silence_ms": self.vad_silence_ms,
            "vad_min_speech_ms": self.vad_min_speech_ms,
            "vad_preroll_ms": self.vad_preroll_ms,
            "stt_model": self.stt_model,
            "stt_chunk_ms": self.stt_chunk_ms,
            "trigger_phrases": self.trigger_phrases,
            "trigger_enabled": self.trigger_enabled,
            "auth_threshold": self.auth_threshold,
            "speaker_model": self.speaker_model,
            "data_dir": str(self.data_dir),
            "save_segment_wav": self.save_segment_wav,
            "queue_maxsize": self.queue_maxsize,
            "session_id": self.session_id,
        }


def ensure_data_dirs(settings: Settings) -> None:
    for rel in ("events", "audio", "voiceprints", "enrollments"):
        (settings.data_dir / rel).mkdir(parents=True, exist_ok=True)
