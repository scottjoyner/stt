from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


SCHEMA_VERSION = "2.0"


class EventBase(BaseModel):
    model_config = ConfigDict(extra="allow")

    schema_version: Literal["2.0"] = SCHEMA_VERSION
    event_id: str
    event_type: str
    session_id: str
    ts_wall: str
    ts_mono_ms: int
    source: str = "stt_service"


class TriggerContext(BaseModel):
    triggered: bool
    trigger_type: str | None = None
    window_id: str | None = None
    window_expires_ts: str | None = None


class Actionability(BaseModel):
    is_actionable: bool
    reason: str
    confidence: float = Field(ge=0.0, le=1.0)


class SpeakerQuality(BaseModel):
    duration_ms: int
    vad_ratio: float
    snr_proxy: float
    clipped: bool
    quality: str
    reason: str


class SpeakerInfo(BaseModel):
    user: str | None = None
    score: float
    threshold: float
    authenticated: bool
    method: str = "ecapa"
    embedding_id: str
    reason: str | None = None


class SegmentFinalEvent(EventBase):
    event_type: Literal["segment_final"] = "segment_final"
    segment_id: str
    conversation_id: str | None = None
    start_mono_ms: int
    end_mono_ms: int
    duration_ms: int
    vad: dict[str, Any]
    transcript_final: str
    trigger_context: TriggerContext
    speaker: SpeakerInfo
    speaker_quality: SpeakerQuality
    actionability: Actionability


class TranscriptPartialEvent(EventBase):
    event_type: Literal["transcript_partial"] = "transcript_partial"
    segment_id: str
    conversation_id: str | None = None
    partial_text: str
    stable_text: str
    progress: float = Field(ge=0.0, le=1.0)
    chunk_idx: int


class ConversationEvent(EventBase):
    event_type: Literal["conversation_start", "conversation_end"]
    conversation_id: str


class PipelineHealthEvent(EventBase):
    event_type: Literal["pipeline_health"] = "pipeline_health"
    audio_queue_depth: int
    vad_latency_ms: float
    stt_processing_ms_avg: float
    dropped_frames: int


def validate_event(payload: dict[str, Any]) -> dict[str, Any]:
    et = payload.get("event_type")
    if et == "segment_final":
        return SegmentFinalEvent.model_validate(payload).model_dump(mode="json")
    if et == "transcript_partial":
        return TranscriptPartialEvent.model_validate(payload).model_dump(mode="json")
    if et in {"conversation_start", "conversation_end"}:
        return ConversationEvent.model_validate(payload).model_dump(mode="json")
    if et == "pipeline_health":
        return PipelineHealthEvent.model_validate(payload).model_dump(mode="json")
    return EventBase.model_validate(payload).model_dump(mode="json")
