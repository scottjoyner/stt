from __future__ import annotations

from stt_service.trigger.base import TriggerDetector, TriggerResult


class TriggerPhraseDetector(TriggerDetector):
    def __init__(self, phrases: list[str]) -> None:
        self.phrases = [p.lower().strip() for p in phrases]

    def evaluate_text(self, text: str) -> TriggerResult:
        lowered = text.lower().strip()
        for phrase in self.phrases:
            if lowered.startswith(phrase):
                return TriggerResult(True, "phrase", 0)
        return TriggerResult(False, None, None)
