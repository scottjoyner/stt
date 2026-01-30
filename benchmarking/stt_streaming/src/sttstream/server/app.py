from __future__ import annotations

import asyncio
import json
from pathlib import Path

from fastapi import FastAPI, WebSocket
from fastapi.responses import JSONResponse

from sttstream.backends.faster_whisper_batch_backend import FasterWhisperBatchBackend
from sttstream.backends.faster_whisper_stream_backend import FasterWhisperStreamBackend
from sttstream.backends.vibevoice_asr_stub import VibeVoiceASRStub
from sttstream.backends.whisper_streaming_backend import WhisperStreamingBackend
from sttstream.server.session_manager import SessionManager
from sttstream.util.logging import setup_logger

logger = setup_logger(__name__)

BACKENDS_STREAM = {
    "faster_whisper_stream": FasterWhisperStreamBackend,
    "whisper_streaming": WhisperStreamingBackend,
}
BACKENDS_BATCH = {
    "faster_whisper_batch": FasterWhisperBatchBackend,
    "vibevoice_asr_stub": VibeVoiceASRStub,
}


def create_app(
    artifacts_dir: Path,
    segment_seconds: float,
    overlap_seconds: float,
    backend_pass1: str,
    backend_pass2: str,
) -> FastAPI:
    app = FastAPI()
    pass1_cls = BACKENDS_STREAM[backend_pass1]
    pass2_cls = BACKENDS_BATCH[backend_pass2]
    manager = SessionManager(
        artifacts_dir=artifacts_dir,
        segment_seconds=segment_seconds,
        overlap_seconds=overlap_seconds,
        pass1=pass1_cls(),
        pass2=pass2_cls(),
    )
    manager.start()

    @app.get("/")
    async def health() -> JSONResponse:
        return JSONResponse({"status": "ok"})

    @app.websocket("/ws")
    async def ws_endpoint(ws: WebSocket) -> None:
        await ws.accept()
        session_state = None
        try:
            while True:
                message = await ws.receive_text()
                payload = json.loads(message)
                msg_type = payload.get("type")
                data = payload.get("data", {})
                if msg_type == "start_session":
                    session_state = manager.create_session(
                        session_id=data["session_id"],
                        sample_rate=data["sample_rate"],
                        channels=data.get("channels", 1),
                    )
                    await ws.send_text(json.dumps({"type": "session_started", "data": {"session_id": session_state.session_id}}))
                elif msg_type == "audio_chunk" and session_state is not None:
                    events = await manager.handle_audio(session_state, data["pcm_bytes"])
                    for event in events:
                        await ws.send_text(json.dumps({"type": event["type"], "data": event}))
                elif msg_type == "end_session" and session_state is not None:
                    events = manager.finalize_session(session_state)
                    for event in events:
                        await ws.send_text(json.dumps({"type": event["type"], "data": event}))
                    await ws.send_text(json.dumps({"type": "session_ended", "data": {"session_id": session_state.session_id}}))
                    break
                await asyncio.sleep(0)
        except Exception as exc:  # pragma: no cover - best effort
            logger.error("websocket error: %s", exc)
        finally:
            await ws.close()

    return app
