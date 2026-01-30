from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from sttstream.backends.base import BatchBackend
from sttstream.util.logging import setup_logger

logger = setup_logger(__name__)

try:  # pragma: no cover
    from faster_whisper import WhisperModel
except Exception:  # pragma: no cover
    WhisperModel = None


@dataclass
class FasterWhisperBatchConfig:
    model: str = "large-v3"
    device: str = "cpu"
    compute_type: str = "int8"
    language: Optional[str] = None


class FasterWhisperBatchBackend(BatchBackend):
    name = "faster_whisper_batch"

    def __init__(self, config: FasterWhisperBatchConfig | None = None):
        self.config = config or FasterWhisperBatchConfig()
        if WhisperModel is None:
            self._model = None
            logger.warning("faster-whisper not installed; batch backend will return placeholder text.")
        else:
            self._model = WhisperModel(self.config.model, device=self.config.device, compute_type=self.config.compute_type)

    def transcribe(self, audio_path: Path) -> str:
        if self._model is None:
            return "[batch backend unavailable]"
        segments, _info = self._model.transcribe(str(audio_path), language=self.config.language, vad_filter=True)
        return " ".join(seg.text.strip() for seg in segments).strip()
