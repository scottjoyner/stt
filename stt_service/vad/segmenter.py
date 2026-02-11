from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

from stt_service.audio.ring_buffer import AudioRingBuffer
from stt_service.config import Settings
from stt_service.vad.base import VAD


@dataclass(slots=True)
class Segment:
    start_mono: float
    end_mono: float
    samples: np.ndarray
    speech_ratio: float


@dataclass
class Segmenter:
    settings: Settings
    vad: VAD
    ring: AudioRingBuffer
    _active: bool = False
    _current_frames: list[np.ndarray] = field(default_factory=list)
    _speech_frames: int = 0
    _total_frames: int = 0
    _start_mono: float = 0.0
    _last_speech_mono: float = 0.0

    def push(self, frame: np.ndarray, monotonic_ts: float) -> tuple[list[dict], list[Segment]]:
        events: list[dict] = []
        completed: list[Segment] = []
        self.ring.append(frame)
        decision = self.vad.is_speech(frame, self.settings.sample_rate)

        frame_duration = len(frame) / self.settings.sample_rate

        if decision.is_speech and not self._active:
            self._active = True
            self._start_mono = monotonic_ts
            self._last_speech_mono = monotonic_ts
            preroll = self.ring.tail(int(self.settings.sample_rate * self.settings.vad_preroll_ms / 1000))
            if len(preroll):
                self._current_frames.append(preroll)
            events.append({"type": "speech_start", "mono_ts": monotonic_ts})

        if self._active:
            self._current_frames.append(frame)
            self._total_frames += 1
            if decision.is_speech:
                self._speech_frames += 1
                self._last_speech_mono = monotonic_ts
            silence_ms = max(0.0, (monotonic_ts - self._last_speech_mono) * 1000)
            duration_ms = (monotonic_ts - self._start_mono + frame_duration) * 1000
            if silence_ms >= self.settings.vad_silence_ms and duration_ms >= self.settings.vad_min_speech_ms:
                audio = np.concatenate(self._current_frames, dtype=np.float32)
                completed.append(
                    Segment(
                        start_mono=self._start_mono,
                        end_mono=monotonic_ts,
                        samples=audio,
                        speech_ratio=self._speech_frames / max(1, self._total_frames),
                    )
                )
                events.append({"type": "speech_end", "mono_ts": monotonic_ts})
                self._active = False
                self._current_frames = []
                self._speech_frames = 0
                self._total_frames = 0

        return events, completed
