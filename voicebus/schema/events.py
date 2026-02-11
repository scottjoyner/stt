from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

SCHEMA_VERSION = "3.0"


class EventBase(BaseModel):
    model_config = ConfigDict(extra="allow")

    schema_version: Literal["3.0"] = SCHEMA_VERSION
    event_id: str
    event_type: str
    session_id: str
    ts_wall: str
    ts_mono_ms: int
    source: str
    conversation_id: str | None = None
    trace_id: str | None = None
    span_id: str | None = None


class TriggerContext(BaseModel):
    triggered: bool
    trigger_type: str | None = None
    window_id: str | None = None
    window_expires_ts: str | None = None


class Actionability(BaseModel):
    is_actionable: bool
    reason: str
    confidence: float = Field(ge=0.0, le=1.0)


class SpeakerInfo(BaseModel):
    user: str | None = None
    score: float
    threshold: float
    authenticated: bool
    method: str = "ecapa"
    embedding_id: str
    reason: str | None = None


class ConversationEvent(EventBase):
    event_type: Literal["conversation_start", "conversation_end"]
    conversation_id: str


class TurnEvent(EventBase):
    event_type: Literal["turn_start", "turn_update", "turn_final"]
    conversation_id: str
    turn_id: str
    transcript_text: str = ""


class SegmentFinalEvent(EventBase):
    event_type: Literal["segment_final"] = "segment_final"
    conversation_id: str | None = None
    turn_id: str | None = None
    segment_id: str
    transcript_final: str
    trigger_context: TriggerContext
    speaker: SpeakerInfo
    actionability: Actionability


class PipelineHealthEvent(EventBase):
    event_type: Literal["pipeline_health"] = "pipeline_health"
    audio_queue_depth: int
    vad_latency_ms: float
    stt_processing_ms_avg: float
    dropped_frames: int


class AgentStepEvent(EventBase):
    event_type: Literal["agent_step_started", "agent_step_result"]
    task_id: str
    run_id: str
    step_id: str
    agent_name: str
    payload: dict[str, Any] = Field(default_factory=dict)


class TTSEvent(EventBase):
    event_type: Literal["tts_started", "tts_chunk", "tts_finished", "tts_interrupted"]
    task_id: str | None = None
    run_id: str | None = None
    chunk_index: int | None = None
    text: str | None = None


def validate_event(payload: dict[str, Any]) -> dict[str, Any]:
    et = payload.get("event_type")
    if et in {"conversation_start", "conversation_end"}:
        return ConversationEvent.model_validate(payload).model_dump(mode="json")
    if et in {"turn_start", "turn_update", "turn_final"}:
        return TurnEvent.model_validate(payload).model_dump(mode="json")
    if et == "segment_final":
        return SegmentFinalEvent.model_validate(payload).model_dump(mode="json")
    if et == "pipeline_health":
        return PipelineHealthEvent.model_validate(payload).model_dump(mode="json")
    if et in {"agent_step_started", "agent_step_result"}:
        return AgentStepEvent.model_validate(payload).model_dump(mode="json")
    if et in {"tts_started", "tts_chunk", "tts_finished", "tts_interrupted"}:
        return TTSEvent.model_validate(payload).model_dump(mode="json")
    return EventBase.model_validate(payload).model_dump(mode="json")
