from __future__ import annotations

import secrets
from pydantic import BaseModel, Field


def _token(n: int = 16) -> str:
    return secrets.token_hex(n)


class TraceContext(BaseModel):
    trace_id: str = Field(default_factory=lambda: _token(16))
    span_id: str = Field(default_factory=lambda: _token(8))
    parent_span_id: str | None = None

    def child(self) -> "TraceContext":
        return TraceContext(trace_id=self.trace_id, parent_span_id=self.span_id)


def new_trace() -> TraceContext:
    return TraceContext()
