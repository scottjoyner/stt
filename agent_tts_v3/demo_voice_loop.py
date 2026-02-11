from __future__ import annotations

import asyncio
from pathlib import Path

from voicebus.transport.ws_client import VoicebusWsClient


def synthesize_tts(text: str) -> None:
    print(f"[TTS] {text}")


async def run_demo() -> None:
    client = VoicebusWsClient("ws://127.0.0.1:8000/ws/events")
    async for event in client.events():
        if event.get("event_type") != "turn_final":
            continue
        actionability = event.get("actionability", {})
        speaker = event.get("speaker", {})
        if not (speaker.get("authenticated") and actionability.get("is_actionable")):
            continue
        task_id = f"task_{event['turn_id']}"
        print({"event_type": "task_created", "task_id": task_id, "conversation_id": event.get("conversation_id")})
        synthesize_tts("Okay—working on it.")
        print({"event_type": "agent_step_started", "task_id": task_id, "agent": "planner"})
        print({"event_type": "agent_step_result", "task_id": task_id, "agent": "executor", "summary": "Done"})
        synthesize_tts("Done. I finished your request.")


if __name__ == "__main__":
    if not Path(".").exists():
        raise SystemExit("workspace missing")
    asyncio.run(run_demo())
