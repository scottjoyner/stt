from __future__ import annotations

from collections import deque

import numpy as np


class AudioRingBuffer:
    def __init__(self, max_samples: int) -> None:
        self._buf: deque[np.ndarray] = deque()
        self._samples = 0
        self._max = max_samples

    def append(self, frame: np.ndarray) -> None:
        self._buf.append(frame)
        self._samples += len(frame)
        while self._samples > self._max and self._buf:
            popped = self._buf.popleft()
            self._samples -= len(popped)

    def tail(self, n_samples: int) -> np.ndarray:
        if not self._buf:
            return np.zeros(0, dtype=np.float32)
        chunks: list[np.ndarray] = []
        need = n_samples
        for frame in reversed(self._buf):
            chunks.append(frame)
            need -= len(frame)
            if need <= 0:
                break
        return np.concatenate(list(reversed(chunks)), dtype=np.float32)[-n_samples:]
