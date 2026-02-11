from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

TaskPriority = Literal["critical", "interactive", "background"]
TaskStatus = Literal["queued", "started", "updated", "completed", "failed", "cancelled"]


class Task(BaseModel):
    schema_version: Literal["3.0"] = "3.0"
    task_id: str
    conversation_id: str
    turn_id: str
    task_signature: str
    priority: TaskPriority = "interactive"
    status: TaskStatus = "queued"
    title: str
    details: str = ""
    metadata: dict = Field(default_factory=dict)


class TaskRun(BaseModel):
    schema_version: Literal["3.0"] = "3.0"
    run_id: str
    task_id: str
    status: Literal["running", "completed", "failed", "cancelled"] = "running"
    lease_expires_at: str | None = None
    heartbeat_ts: str | None = None


class AgentStep(BaseModel):
    schema_version: Literal["3.0"] = "3.0"
    step_id: str
    run_id: str
    agent_name: str
    status: Literal["started", "result"]
    summary: str
    artifact_ref: str | None = None
