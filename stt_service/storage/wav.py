from __future__ import annotations

import wave
from datetime import datetime, timezone
from pathlib import Path

import numpy as np


class SegmentWavWriter:
    def __init__(self, root: Path, sample_rate: int) -> None:
        self.root = root
        self.sample_rate = sample_rate

    def save(self, segment_id: str, audio: np.ndarray) -> Path:
        now = datetime.now(tz=timezone.utc)
        folder = self.root / "audio" / f"{now.year:04d}" / f"{now.month:02d}" / f"{now.day:02d}"
        folder.mkdir(parents=True, exist_ok=True)
        path = folder / f"{segment_id}.wav"
        pcm = np.clip(audio, -1.0, 1.0)
        pcm = (pcm * 32767).astype(np.int16)
        with wave.open(str(path), "wb") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(self.sample_rate)
            wf.writeframes(pcm.tobytes())
        return path
