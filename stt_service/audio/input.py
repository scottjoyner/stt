from __future__ import annotations

import logging
import queue
from dataclasses import dataclass

import numpy as np

from stt_service.config import Settings

LOGGER = logging.getLogger(__name__)

try:
    import sounddevice as sd
except Exception:  # pragma: no cover
    sd = None


@dataclass(slots=True)
class AudioFrame:
    samples: np.ndarray
    monotonic_ts: float


class MicrophoneInput:
    def __init__(self, settings: Settings, frame_queue: queue.Queue[AudioFrame]) -> None:
        self.settings = settings
        self.frame_queue = frame_queue
        self._stream = None

    def start(self) -> None:
        if sd is None:
            raise RuntimeError("sounddevice not installed")

        blocksize = int(self.settings.sample_rate * self.settings.frame_ms / 1000)

        def callback(indata: np.ndarray, frames: int, _time, status) -> None:
            if status:
                LOGGER.warning("audio_status=%s", status)
            mono = np.asarray(indata[:, 0], dtype=np.float32)
            try:
                self.frame_queue.put_nowait(AudioFrame(samples=mono, monotonic_ts=_time.inputBufferAdcTime))
            except queue.Full:
                _ = self.frame_queue.get_nowait()
                self.frame_queue.put_nowait(AudioFrame(samples=mono, monotonic_ts=_time.inputBufferAdcTime))

        self._stream = sd.InputStream(
            samplerate=self.settings.sample_rate,
            channels=self.settings.channels,
            dtype="float32",
            blocksize=blocksize,
            callback=callback,
        )
        self._stream.start()
        LOGGER.info("microphone_started")

    def stop(self) -> None:
        if self._stream is not None:
            self._stream.stop()
            self._stream.close()
            self._stream = None
            LOGGER.info("microphone_stopped")
