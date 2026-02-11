from __future__ import annotations

import wave
from pathlib import Path

import numpy as np


def read_wav_mono_16k(path: Path) -> np.ndarray:
    with wave.open(str(path), "rb") as wf:
        sr = wf.getframerate()
        ch = wf.getnchannels()
        data = wf.readframes(wf.getnframes())
    pcm = np.frombuffer(data, dtype=np.int16).astype(np.float32) / 32768.0
    if ch > 1:
        pcm = pcm.reshape(-1, ch).mean(axis=1)
    if sr != 16_000:
        raise ValueError(f"Expected 16kHz wav for test mode, got {sr}")
    return pcm
