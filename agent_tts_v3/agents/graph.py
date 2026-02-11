from __future__ import annotations

from dataclasses import dataclass

from voicebus.schema.tasks import Task


@dataclass
class UserIntent:
    text: str
    actionable: bool
    needs_code: bool


class TaskRouter:
    CODE_HINTS = ("write code", "fix bug", "generate script", "refactor")

    def route(self, intent: UserIntent) -> list[str]:
        base = ["turn_interpreter", "planner", "executor", "verifier", "summarizer", "tts_speaker"]
        if intent.needs_code:
            return ["turn_interpreter", "planner", "coding_agent", "verifier", "summarizer", "tts_speaker"]
        return base


class TurnInterpreter:
    def parse(self, text: str, actionable: bool) -> UserIntent:
        lowered = text.lower()
        needs_code = any(h in lowered for h in TaskRouter.CODE_HINTS)
        return UserIntent(text=text, actionable=actionable, needs_code=needs_code)


def plan_for_task(task: Task) -> dict:
    return {
        "task_id": task.task_id,
        "acceptance_criteria": [
            "respond concisely",
            "emit agent_step_result",
            "attach artifacts if code changes",
        ],
    }
