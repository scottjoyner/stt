from __future__ import annotations

from dataclasses import dataclass

from stt_service.utils.ids import new_event_id


@dataclass
class ConversationGroup:
    silence_seconds: int
    conversation_id: str | None = None
    last_activity_mono: float | None = None

    def on_segment_start(self, mono_ts: float) -> tuple[str | None, str | None]:
        started = None
        ended = None
        if self.conversation_id is None:
            self.conversation_id = new_event_id()
            started = self.conversation_id
        elif self.last_activity_mono is not None and (mono_ts - self.last_activity_mono) > self.silence_seconds:
            ended = self.conversation_id
            self.conversation_id = new_event_id()
            started = self.conversation_id
        return started, ended

    def touch(self, mono_ts: float) -> None:
        self.last_activity_mono = mono_ts

    def current(self) -> str | None:
        return self.conversation_id
