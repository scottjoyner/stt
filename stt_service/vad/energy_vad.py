from __future__ import annotations

import numpy as np

from stt_service.vad.base import VAD, VADDecision


class EnergyVAD(VAD):
    def __init__(self, threshold: float = 0.015) -> None:
        self.threshold = threshold

    def is_speech(self, frame: np.ndarray, sample_rate: int) -> VADDecision:
        del sample_rate
        rms = float(np.sqrt(np.mean(np.square(frame)) + 1e-9))
        return VADDecision(is_speech=rms >= self.threshold, score=rms)
