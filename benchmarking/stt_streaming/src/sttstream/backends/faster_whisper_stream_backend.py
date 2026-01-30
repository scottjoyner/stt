from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

import numpy as np

from sttstream.backends.base import PartialResult, StreamingBackend
from sttstream.util.logging import setup_logger

logger = setup_logger(__name__)


try:  # pragma: no cover - import handled at runtime
    from faster_whisper import WhisperModel
except Exception:  # pragma: no cover
    WhisperModel = None


def _lcp(a: str, b: str) -> str:
    end = min(len(a), len(b))
    i = 0
    while i < end and a[i] == b[i]:
        i += 1
    return a[:i]


@dataclass
class FasterWhisperStreamConfig:
    model: str = "small"
    device: str = "cpu"
    compute_type: str = "int8"
    language: Optional[str] = None
    decode_interval_s: float = 0.6
    overlap_s: float = 1.0


class FasterWhisperStreamBackend(StreamingBackend):
    name = "faster_whisper_stream"

    def __init__(self, config: FasterWhisperStreamConfig | None = None):
        self.config = config or FasterWhisperStreamConfig()
        self._model = None
        if WhisperModel is not None:
            self._model = WhisperModel(self.config.model, device=self.config.device, compute_type=self.config.compute_type)
        else:
            logger.warning("faster-whisper not installed; streaming backend will return placeholder text.")
        self.reset()

    def reset(self) -> None:
        self._buffer = np.zeros(0, dtype=np.float32)
        self._last_text = ""
        self._elapsed_since_decode = 0.0

    def _decode(self, audio: np.ndarray, sample_rate: int) -> str:
        if self._model is None:
            return "[streaming backend unavailable]"
        segments, _info = self._model.transcribe(audio, language=self.config.language, vad_filter=False)
        return " ".join(seg.text.strip() for seg in segments).strip()

    def process_audio(self, audio: np.ndarray, sample_rate: int) -> PartialResult | None:
        if audio.size == 0:
            return None
        self._buffer = np.concatenate([self._buffer, audio])
        self._elapsed_since_decode += audio.size / sample_rate
        if self._elapsed_since_decode < self.config.decode_interval_s:
            return None
        self._elapsed_since_decode = 0.0
        if self._buffer.size < int(sample_rate * 0.2):
            return None
        text = self._decode(self._buffer, sample_rate)
        lcp = _lcp(self._last_text, text)
        stability = len(lcp) / max(len(text), 1)
        self._last_text = text
        return PartialResult(text=text, stability=stability)

    def finalize(self, audio: np.ndarray, sample_rate: int) -> str:
        return self._decode(audio, sample_rate)
