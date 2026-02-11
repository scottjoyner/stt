from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass(slots=True)
class TranscriptChunk:
    text: str
    avg_logprob: float | None = None
    no_speech_prob: float | None = None


class StreamingTranscriber:
    def partial(self, audio: np.ndarray, sample_rate: int) -> TranscriptChunk:
        raise NotImplementedError

    def final(self, audio: np.ndarray, sample_rate: int) -> TranscriptChunk:
        raise NotImplementedError
