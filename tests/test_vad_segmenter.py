from __future__ import annotations

import numpy as np

from stt_service.audio.ring_buffer import AudioRingBuffer
from stt_service.config import Settings
from stt_service.vad.energy_vad import EnergyVAD
from stt_service.vad.segmenter import Segmenter


def test_segmenter_detects_speech_segment() -> None:
    settings = Settings(
        STT_SAMPLE_RATE=16_000,
        VAD_SILENCE_MS=200,
        vad_min_speech_ms=100,
        vad_preroll_ms=100,
        vad_energy_threshold=0.01,
    )
    seg = Segmenter(settings, EnergyVAD(0.01), AudioRingBuffer(16_000))
    frame = int(settings.sample_rate * settings.frame_ms / 1000)

    t = 0.0
    for _ in range(10):
        seg.push(np.zeros(frame, dtype=np.float32), t)
        t += settings.frame_ms / 1000

    completed = []
    for _ in range(20):
        _, done = seg.push(np.ones(frame, dtype=np.float32) * 0.05, t)
        completed.extend(done)
        t += settings.frame_ms / 1000

    for _ in range(15):
        _, done = seg.push(np.zeros(frame, dtype=np.float32), t)
        completed.extend(done)
        t += settings.frame_ms / 1000

    assert completed
    assert completed[0].speech_ratio > 0.4
