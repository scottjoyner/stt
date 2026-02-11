from __future__ import annotations

from dataclasses import dataclass

from stt_service.utils.ids import new_event_id


@dataclass
class TriggerWindowState:
    window_seconds: int
    window_id: str | None = None
    expires_mono: float = 0.0
    trigger_type: str | None = None

    def open(self, mono_ts: float, trigger_type: str) -> str:
        self.window_id = new_event_id()
        self.expires_mono = mono_ts + self.window_seconds
        self.trigger_type = trigger_type
        return self.window_id

    def context(self, mono_ts: float) -> dict[str, str | bool | None]:
        active = self.window_id is not None and mono_ts <= self.expires_mono
        return {
            "triggered": active,
            "trigger_type": self.trigger_type if active else None,
            "window_id": self.window_id if active else None,
        }
