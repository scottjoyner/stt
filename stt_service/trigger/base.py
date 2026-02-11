from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class TriggerResult:
    triggered: bool
    trigger_type: str | None
    offset_ms: int | None


class TriggerDetector:
    def evaluate_audio(self, _: bytes) -> TriggerResult:
        return TriggerResult(triggered=False, trigger_type=None, offset_ms=None)

    def evaluate_text(self, text: str) -> TriggerResult:
        raise NotImplementedError
