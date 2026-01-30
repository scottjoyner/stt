from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path

import numpy as np


@dataclass
class PartialResult:
    text: str
    stability: float


class StreamingBackend(ABC):
    name: str

    @abstractmethod
    def reset(self) -> None:
        raise NotImplementedError

    @abstractmethod
    def process_audio(self, audio: np.ndarray, sample_rate: int) -> PartialResult | None:
        raise NotImplementedError

    @abstractmethod
    def finalize(self, audio: np.ndarray, sample_rate: int) -> str:
        raise NotImplementedError


class BatchBackend(ABC):
    name: str

    @abstractmethod
    def transcribe(self, audio_path: Path) -> str:
        raise NotImplementedError
