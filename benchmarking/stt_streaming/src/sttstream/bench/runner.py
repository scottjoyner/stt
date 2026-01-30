from __future__ import annotations

import asyncio
import base64
import json
import time
import uuid
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import websockets
import yaml

from sttstream.bench.datasets import DatasetItem, load_manifest
from sttstream.bench.metrics import compute_metrics
from sttstream.util.audio import read_wav
from sttstream.util.db import init_db
from sttstream.util.time import now_ms


@dataclass
class BenchConfig:
    chunk_ms: int = 200


def _load_config(path: Path) -> BenchConfig:
    if not path.exists():
        return BenchConfig()
    data = yaml.safe_load(path.read_text()) or {}
    return BenchConfig(chunk_ms=int(data.get("chunk_ms", 200)))


async def _stream_session(ws_url: str, item: DatasetItem, config: BenchConfig) -> dict:
    audio, sample_rate = read_wav(item.audio_path)
    chunk_samples = int(sample_rate * (config.chunk_ms / 1000.0))
    session_id = f"bench-{item.id}-{uuid.uuid4().hex[:6]}"
    events: list[dict] = []
    partials: list[str] = []
    final_text = ""
    refined_text = ""
    t_start = now_ms()
    ttft_ms = 0.0
    ttfinal_ms = 0.0
    ttrefine_ms = 0.0

    async with websockets.connect(ws_url) as ws:
        await ws.send(json.dumps({
            "type": "start_session",
            "data": {
                "sample_rate": sample_rate,
                "channels": 1,
                "session_id": session_id,
            },
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
            await asyncio.sleep(config.chunk_ms / 1000.0)
            while True:
                try:
                    msg = await asyncio.wait_for(ws.recv(), timeout=0.01)
                except asyncio.TimeoutError:
                    break
                event = json.loads(msg)
                events.append(event)
                if event["type"] == "partial_transcript":
                    text = event["data"]["text"]
                    partials.append(text)
                    if ttft_ms == 0.0:
                        ttft_ms = event["data"]["t_server_ms"] - t_start
                elif event["type"] == "final_transcript":
                    final_text = event["data"]["text"]
                    ttfinal_ms = event["data"]["t_server_ms"] - t_start
                elif event["type"] == "refined_transcript":
                    refined_text = event["data"]["text"]
                    ttrefine_ms = event["data"]["t_server_ms"] - t_start
        await ws.send(json.dumps({"type": "end_session", "data": {}}))
        end_wait = time.time() + 5.0
        while time.time() < end_wait:
            try:
                msg = await asyncio.wait_for(ws.recv(), timeout=0.2)
            except asyncio.TimeoutError:
                break
            event = json.loads(msg)
            events.append(event)
            if event["type"] == "final_transcript":
                final_text = event["data"]["text"]
                ttfinal_ms = event["data"]["t_server_ms"] - t_start
            if event["type"] == "refined_transcript":
                refined_text = event["data"]["text"]
                ttrefine_ms = event["data"]["t_server_ms"] - t_start

    metrics = compute_metrics(
        reference=item.text,
        final_text=final_text,
        refined_text=refined_text,
        partials=partials,
        ttft_ms=ttft_ms,
        ttfinal_ms=ttfinal_ms,
        ttrefine_ms=ttrefine_ms,
    )
    return {
        "metrics": metrics,
        "session_id": session_id,
        "partials": partials,
        "final_text": final_text,
        "refined_text": refined_text,
    }


async def run_benchmark(ws_url: str, dataset_path: Path, config_path: Path, output_dir: Path) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    config = _load_config(config_path)
    items = load_manifest(dataset_path)
    db_path = output_dir / "results.sqlite"
    conn = init_db(db_path)
    conn.execute(
        "INSERT OR REPLACE INTO runs (id, created_at_ms, config_json) VALUES (?, ?, ?)",
        (output_dir.name, now_ms(), config_path.read_text() if config_path.exists() else "{}"),
    )
    conn.commit()
    for item in items:
        result = await _stream_session(ws_url, item, config)
        metrics = result["metrics"]
        conn.execute(
            "INSERT OR REPLACE INTO sessions (id, run_id, created_at_ms, sample_rate, channels) VALUES (?, ?, ?, ?, ?)",
            (result["session_id"], output_dir.name, now_ms(), 0, 1),
        )
        conn.execute(
            "INSERT INTO metrics (run_id, session_id, key, value) VALUES (?, ?, ?, ?)",
            (output_dir.name, result["session_id"], "ttft_ms", metrics.ttft_ms),
        )
        conn.execute(
            "INSERT INTO metrics (run_id, session_id, key, value) VALUES (?, ?, ?, ?)",
            (output_dir.name, result["session_id"], "ttfinal_ms", metrics.ttfinal_ms),
        )
        conn.execute(
            "INSERT INTO metrics (run_id, session_id, key, value) VALUES (?, ?, ?, ?)",
            (output_dir.name, result["session_id"], "ttrefine_ms", metrics.ttrefine_ms),
        )
        conn.execute(
            "INSERT INTO metrics (run_id, session_id, key, value) VALUES (?, ?, ?, ?)",
            (output_dir.name, result["session_id"], "churn", metrics.churn),
        )
        conn.execute(
            "INSERT INTO metrics (run_id, session_id, key, value) VALUES (?, ?, ?, ?)",
            (output_dir.name, result["session_id"], "wer_final", metrics.wer_final),
        )
        conn.execute(
            "INSERT INTO metrics (run_id, session_id, key, value) VALUES (?, ?, ?, ?)",
            (output_dir.name, result["session_id"], "wer_refined", metrics.wer_refined),
        )
        conn.execute(
            "INSERT INTO metrics (run_id, session_id, key, value) VALUES (?, ?, ?, ?)",
            (output_dir.name, result["session_id"], "cer_final", metrics.cer_final),
        )
        conn.execute(
            "INSERT INTO metrics (run_id, session_id, key, value) VALUES (?, ?, ?, ?)",
            (output_dir.name, result["session_id"], "cer_refined", metrics.cer_refined),
        )
        conn.commit()
    return db_path
