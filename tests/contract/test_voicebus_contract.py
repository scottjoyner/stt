from __future__ import annotations

import json
from pathlib import Path

from voicebus.schema.events import validate_event
from voicebus.schema.tasks import Task


def test_example_payloads_validate() -> None:
    payloads = json.loads(Path("voicebus/examples/events.json").read_text())
    validate_event(payloads["turn_final"])
    validate_event(payloads["agent_step_result"])
    validate_event(payloads["tts_chunk"])


def test_task_model() -> None:
    task = Task(
        task_id="task_01",
        conversation_id="conv_01",
        turn_id="turn_01",
        task_signature="sig01",
        title="Do it",
    )
    assert task.schema_version == "3.0"
