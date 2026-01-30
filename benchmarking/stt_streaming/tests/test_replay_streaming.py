import asyncio
import base64
import json
import socket
import threading
from pathlib import Path

import numpy as np
import pytest
import uvicorn
import websockets

from sttstream.server.app import create_app
from sttstream.util.audio import read_wav
from sttstream.util.sample_data import generate_sine_wav, write_text


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("", 0))
        return s.getsockname()[1]


def _run_server(host: str, port: int, artifacts_dir: Path) -> uvicorn.Server:
    app = create_app(
        artifacts_dir=artifacts_dir,
        segment_seconds=0.5,
        overlap_seconds=0.1,
        backend_pass1="faster_whisper_stream",
        backend_pass2="faster_whisper_batch",
    )
    config = uvicorn.Config(app, host=host, port=port, log_level="info")
    server = uvicorn.Server(config)

    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()
    return server


@pytest.mark.asyncio
async def test_replay_streaming(tmp_path: Path) -> None:
    port = _free_port()
    artifacts_dir = tmp_path / "runs"
    server = _run_server("127.0.0.1", port, artifacts_dir)
    ws_url = f"ws://127.0.0.1:{port}/ws"

    wav_path = tmp_path / "sample.wav"
    text_path = tmp_path / "sample.txt"
    generate_sine_wav(wav_path, duration_s=1.0)
    write_text(text_path, "hello world")
    audio, sample_rate = read_wav(wav_path)
    chunk_ms = 200
    chunk_samples = int(sample_rate * (chunk_ms / 1000.0))

    partials = []
    finals = []
    refined = []

    async with websockets.connect(ws_url) as ws:
        await ws.send(json.dumps({
            "type": "start_session",
            "data": {"sample_rate": sample_rate, "channels": 1, "session_id": "test"},
        }))
        await ws.recv()
        for i in range(0, len(audio), chunk_samples):
            chunk = audio[i : i + chunk_samples]
            payload = {
                "type": "audio_chunk",
                "data": {
                    "sequence": i // chunk_samples,
                    "pcm_bytes": base64.b64encode((chunk * 32767.0).astype(np.int16).tobytes()).decode("ascii"),
                    "t_client_ms": 0,
                },
            }
            await ws.send(json.dumps(payload))
            await asyncio.sleep(chunk_ms / 1000.0)
            while True:
                try:
                    msg = await asyncio.wait_for(ws.recv(), timeout=0.01)
                except asyncio.TimeoutError:
                    break
                event = json.loads(msg)
                if event["type"] == "partial_transcript":
                    partials.append(event)
                if event["type"] == "final_transcript":
                    finals.append(event)
                if event["type"] == "refined_transcript":
                    refined.append(event)
        await ws.send(json.dumps({"type": "end_session", "data": {}}))
        end_wait = asyncio.get_event_loop().time() + 5.0
        while asyncio.get_event_loop().time() < end_wait:
            try:
                msg = await asyncio.wait_for(ws.recv(), timeout=0.2)
            except asyncio.TimeoutError:
                break
            event = json.loads(msg)
            if event["type"] == "partial_transcript":
                partials.append(event)
            if event["type"] == "final_transcript":
                finals.append(event)
            if event["type"] == "refined_transcript":
                refined.append(event)

    assert partials
    assert finals
    assert refined

    session_dir = artifacts_dir / "test"
    assert (session_dir / "session.wav").exists()
    assert any(path.name.startswith("segment_") for path in session_dir.glob("segment_*.wav"))
    assert (artifacts_dir / "results.sqlite").exists()

    server.should_exit = True
