from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass(slots=True)
class VADDecision:
    is_speech: bool
    score: float


class VAD:
    def is_speech(self, frame: np.ndarray, sample_rate: int) -> VADDecision:
        raise NotImplementedError
