from __future__ import annotations

import logging

import numpy as np

from stt_service.stt.base import StreamingTranscriber, TranscriptChunk

LOGGER = logging.getLogger(__name__)

try:
    from faster_whisper import WhisperModel
except Exception:  # pragma: no cover
    WhisperModel = None


class FasterWhisperTranscriber(StreamingTranscriber):
    def __init__(self, model_name: str = "base") -> None:
        self.model_name = model_name
        self._model = WhisperModel(model_name, device="cpu", compute_type="int8") if WhisperModel else None

    def _run(self, audio: np.ndarray) -> TranscriptChunk:
        if self._model is None:
            # lightweight fallback for local testing without model download
            seconds = len(audio) / 16_000
            return TranscriptChunk(text=f"[stub transcript {seconds:.2f}s]", avg_logprob=None)

        segments, info = self._model.transcribe(audio, language="en", vad_filter=False)
        text = " ".join(seg.text.strip() for seg in segments).strip()
        return TranscriptChunk(text=text, avg_logprob=getattr(info, "avg_logprob", None))

    def partial(self, audio: np.ndarray, sample_rate: int) -> TranscriptChunk:
        del sample_rate
        return self._run(audio)

    def final(self, audio: np.ndarray, sample_rate: int) -> TranscriptChunk:
        del sample_rate
        return self._run(audio)
