from __future__ import annotations

from stt_service.trigger.base import TriggerDetector, TriggerResult


class WakeWordStubDetector(TriggerDetector):
    """Placeholder wake word detector.

    TODO: replace with an actual wake-word engine (Porcupine/OpenWakeWord/etc.) and emit
    frame-level detection offsets from the audio stream.
    """

    def evaluate_text(self, text: str) -> TriggerResult:
        del text
        return TriggerResult(False, None, None)
