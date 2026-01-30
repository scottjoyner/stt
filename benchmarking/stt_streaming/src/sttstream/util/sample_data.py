from __future__ import annotations

import math
import wave
from array import array
from pathlib import Path


def generate_sine_wav(path: Path, duration_s: float = 1.0, sample_rate: int = 16000, freq_hz: float = 440.0) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    frames = int(sample_rate * duration_s)
    values = array("h")
    for i in range(frames):
        sample = int(0.2 * 32767 * math.sin(2 * math.pi * freq_hz * (i / sample_rate)))
        values.append(sample)
    with wave.open(str(path), "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        wf.writeframes(values.tobytes())
    return path


def write_text(path: Path, text: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)
    return path
