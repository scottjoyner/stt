from __future__ import annotations

import wave
from pathlib import Path
from typing import Iterable

import numpy as np


def pcm16le_to_float32(pcm_bytes: bytes) -> np.ndarray:
    audio = np.frombuffer(pcm_bytes, dtype=np.int16).astype(np.float32)
    return audio / 32768.0


def float32_to_pcm16le(audio: np.ndarray) -> bytes:
    audio = np.clip(audio, -1.0, 1.0)
    return (audio * 32767.0).astype(np.int16).tobytes()


def read_wav(path: Path) -> tuple[np.ndarray, int]:
    with wave.open(str(path), "rb") as wf:
        sr = wf.getframerate()
        data = wf.readframes(wf.getnframes())
    audio = pcm16le_to_float32(data)
    return audio, sr


def write_wav(path: Path, audio: np.ndarray, sample_rate: int) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(path), "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        wf.writeframes(float32_to_pcm16le(audio))


def concat_audio(chunks: Iterable[np.ndarray]) -> np.ndarray:
    return np.concatenate([c for c in chunks if c.size > 0])
