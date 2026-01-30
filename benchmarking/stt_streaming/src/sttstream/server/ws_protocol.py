from __future__ import annotations

from pydantic import BaseModel


class StartSession(BaseModel):
    sample_rate: int
    channels: int
    encoding: str = "pcm_s16le"
    session_id: str


class AudioChunk(BaseModel):
    sequence: int
    pcm_bytes: str
    t_client_ms: int


class EndSession(BaseModel):
    reason: str | None = None


class PartialTranscript(BaseModel):
    t_server_ms: int
    text: str
    segment_id: str
    stability_score: float


class FinalTranscript(BaseModel):
    t_server_ms: int
    text: str
    segment_id: str


class RefinedTranscript(BaseModel):
    t_server_ms: int
    text: str
    segment_id: str
    pass2_backend: str


class MetricsUpdate(BaseModel):
    t_server_ms: int
    metrics: dict
