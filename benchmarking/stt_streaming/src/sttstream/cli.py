from __future__ import annotations

import argparse
import asyncio
import base64
import json
import time
from pathlib import Path

import numpy as np
import sounddevice as sd
import uvicorn
import websockets

from sttstream.bench.report import export_markdown_report
from sttstream.bench.runner import run_benchmark
from sttstream.server.app import create_app
from sttstream.util.audio import read_wav
from sttstream.util.logging import setup_logger
from sttstream.util.time import now_ms
from sttstream.util.wer import wer

logger = setup_logger(__name__)


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(prog="sttstream")
    sub = parser.add_subparsers(dest="cmd", required=True)

    serve = sub.add_parser("serve")
    serve.add_argument("--host", default="0.0.0.0")
    serve.add_argument("--port", type=int, default=8765)
    serve.add_argument("--backend-pass1", default="faster_whisper_stream")
    serve.add_argument("--backend-pass2", default="faster_whisper_batch")
    serve.add_argument("--segment-seconds", type=float, default=4.0)
    serve.add_argument("--overlap-seconds", type=float, default=0.5)
    serve.add_argument("--artifacts-dir", type=Path, default=Path("runs"))

    mic = sub.add_parser("mic")
    mic.add_argument("--url", required=True)
    mic.add_argument("--session-id", required=True)
    mic.add_argument("--sample-rate", type=int, default=16000)
    mic.add_argument("--chunk-ms", type=int, default=200)

    replay = sub.add_parser("replay")
    replay.add_argument("--url", required=True)
    replay.add_argument("--wav", type=Path, required=True)
    replay.add_argument("--text", type=Path, required=False)
    replay.add_argument("--chunk-ms", type=int, default=200)

    bench = sub.add_parser("bench")
    bench.add_argument("--url", default="ws://localhost:8765/ws")
    bench.add_argument("--dataset", type=Path, required=True)
    bench.add_argument("--configs", type=Path, required=False, default=Path("configs/bench.yaml"))
    bench.add_argument("--out", type=Path, required=True)

    report = sub.add_parser("export-report")
    report.add_argument("--run", type=Path, required=True)
    report.add_argument("--out", type=Path, default=Path("report.md"))

    return parser.parse_args()


async def _send_audio(ws_url: str, session_id: str, sample_rate: int, chunk_ms: int, audio: np.ndarray) -> dict:
    chunk_samples = int(sample_rate * (chunk_ms / 1000.0))
    final_text = ""
    refined_text = ""
    async with websockets.connect(ws_url) as ws:
        await ws.send(json.dumps({
            "type": "start_session",
            "data": {"sample_rate": sample_rate, "channels": 1, "session_id": session_id},
        }))
        await ws.recv()
        for i in range(0, len(audio), chunk_samples):
            chunk = audio[i : i + chunk_samples]
            payload = {
                "type": "audio_chunk",
                "data": {
                    "sequence": i // chunk_samples,
                    "pcm_bytes": base64.b64encode((chunk * 32767.0).astype(np.int16).tobytes()).decode("ascii"),
                    "t_client_ms": now_ms(),
                },
            }
            await ws.send(json.dumps(payload))
            await asyncio.sleep(chunk_ms / 1000.0)
            while True:
                try:
                    msg = await asyncio.wait_for(ws.recv(), timeout=0.01)
                except asyncio.TimeoutError:
                    break
                logger.info("event: %s", msg)
                event = json.loads(msg)
                if event["type"] == "final_transcript":
                    final_text = event["data"]["text"]
                if event["type"] == "refined_transcript":
                    refined_text = event["data"]["text"]
        await ws.send(json.dumps({"type": "end_session", "data": {}}))
        while True:
            try:
                msg = await asyncio.wait_for(ws.recv(), timeout=0.2)
            except asyncio.TimeoutError:
                break
            logger.info("event: %s", msg)
            event = json.loads(msg)
            if event["type"] == "final_transcript":
                final_text = event["data"]["text"]
            if event["type"] == "refined_transcript":
                refined_text = event["data"]["text"]
    return {"final": final_text, "refined": refined_text}


async def cmd_mic(args: argparse.Namespace) -> None:
    buffer: list[np.ndarray] = []
    sample_rate = args.sample_rate
    chunk_samples = int(sample_rate * (args.chunk_ms / 1000.0))

    def _callback(indata, frames, time_info, status) -> None:
        if status:
            logger.warning("audio status: %s", status)
        buffer.append(indata.copy().reshape(-1))

    async with websockets.connect(args.url) as ws:
        await ws.send(json.dumps({
            "type": "start_session",
            "data": {"sample_rate": sample_rate, "channels": 1, "session_id": args.session_id},
        }))
        await ws.recv()
        with sd.InputStream(channels=1, samplerate=sample_rate, callback=_callback):
            logger.info("Recording... Press Ctrl+C to stop.")
            try:
                while True:
                    time.sleep(0.05)
                    if sum(chunk.size for chunk in buffer) >= chunk_samples:
                        audio = np.concatenate(buffer)
                        buffer.clear()
                        payload = {
                            "type": "audio_chunk",
                            "data": {
                                "sequence": int(time.time() * 1000),
                                "pcm_bytes": base64.b64encode((audio * 32767.0).astype(np.int16).tobytes()).decode("ascii"),
                                "t_client_ms": now_ms(),
                            },
                        }
                        await ws.send(json.dumps(payload))
                        while True:
                            try:
                                msg = await asyncio.wait_for(ws.recv(), timeout=0.01)
                            except asyncio.TimeoutError:
                                break
                            logger.info("event: %s", msg)
            except KeyboardInterrupt:
                logger.info("Stopping mic capture")
        await ws.send(json.dumps({"type": "end_session", "data": {}}))


async def cmd_replay(args: argparse.Namespace) -> None:
    audio, sample_rate = read_wav(args.wav)
    results = await _send_audio(args.url, args.wav.stem, sample_rate, args.chunk_ms, audio)
    if args.text and args.text.exists():
        reference = args.text.read_text()
        if results["final"]:
            logger.info("final WER: %.4f", wer(reference, results["final"]))
        if results["refined"]:
            logger.info("refined WER: %.4f", wer(reference, results["refined"]))


def cmd_serve(args: argparse.Namespace) -> None:
    app = create_app(
        artifacts_dir=args.artifacts_dir,
        segment_seconds=args.segment_seconds,
        overlap_seconds=args.overlap_seconds,
        backend_pass1=args.backend_pass1,
        backend_pass2=args.backend_pass2,
    )
    uvicorn.run(app, host=args.host, port=args.port)


def cmd_report(args: argparse.Namespace) -> None:
    export_markdown_report(args.run, args.out)
    logger.info("report written to %s", args.out)


def main() -> None:
    args = _parse_args()
    if args.cmd == "serve":
        cmd_serve(args)
    elif args.cmd == "mic":
        asyncio.run(cmd_mic(args))
    elif args.cmd == "replay":
        asyncio.run(cmd_replay(args))
    elif args.cmd == "bench":
        asyncio.run(run_benchmark(args.url, args.dataset, args.configs, args.out))
    elif args.cmd == "export-report":
        cmd_report(args)


if __name__ == "__main__":
    main()
