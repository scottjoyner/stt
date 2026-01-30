from __future__ import annotations

import asyncio
import base64
import uuid
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np

from sttstream.backends.base import BatchBackend, StreamingBackend
from sttstream.util.audio import concat_audio, pcm16le_to_float32, write_wav
from sttstream.util.db import init_db
from sttstream.util.logging import setup_logger
from sttstream.util.time import now_ms

logger = setup_logger(__name__)


@dataclass
class SegmentInfo:
    id: str
    start_ms: int
    end_ms: int
    audio: np.ndarray
    audio_path: Path


@dataclass
class SessionState:
    session_id: str
    sample_rate: int
    channels: int
    artifacts_dir: Path
    pass1: StreamingBackend
    pass2: BatchBackend
    buffer: list[np.ndarray] = field(default_factory=list)
    full_audio: list[np.ndarray] = field(default_factory=list)
    segment_index: int = 0
    last_segment_start_ms: int = field(default_factory=now_ms)
    session_start_ms: int = field(default_factory=now_ms)
    events: list[dict] = field(default_factory=list)


class SessionManager:
    def __init__(
        self,
        artifacts_dir: Path,
        segment_seconds: float,
        overlap_seconds: float,
        pass1: StreamingBackend,
        pass2: BatchBackend,
    ) -> None:
        self.artifacts_dir = artifacts_dir
        self.segment_seconds = segment_seconds
        self.overlap_seconds = overlap_seconds
        self.pass1 = pass1
        self.pass2 = pass2
        self.sessions: dict[str, SessionState] = {}
        self._refine_queue: asyncio.Queue[tuple[SessionState, SegmentInfo]] = asyncio.Queue()
        self._refine_task: asyncio.Task | None = None
        self.db_conn = init_db(self.artifacts_dir / "results.sqlite")

    def start(self) -> None:
        if self._refine_task is None:
            self._refine_task = asyncio.create_task(self._refine_worker())

    def create_session(self, session_id: str, sample_rate: int, channels: int) -> SessionState:
        session_dir = self.artifacts_dir / session_id
        session_dir.mkdir(parents=True, exist_ok=True)
        state = SessionState(
            session_id=session_id,
            sample_rate=sample_rate,
            channels=channels,
            artifacts_dir=session_dir,
            pass1=self.pass1,
            pass2=self.pass2,
        )
        state.pass1.reset()
        self.sessions[session_id] = state
        self.db_conn.execute(
            "INSERT OR REPLACE INTO sessions (id, run_id, created_at_ms, sample_rate, channels) VALUES (?, ?, ?, ?, ?)",
            (session_id, "local", now_ms(), sample_rate, channels),
        )
        self.db_conn.commit()
        return state

    def get_session(self, session_id: str) -> SessionState:
        return self.sessions[session_id]

    async def handle_audio(self, state: SessionState, pcm_b64: str) -> list[dict]:
        pcm_bytes = base64.b64decode(pcm_b64)
        audio = pcm16le_to_float32(pcm_bytes)
        state.buffer.append(audio)
        state.full_audio.append(audio)
        partial = state.pass1.process_audio(audio, state.sample_rate)
        events: list[dict] = []
        if partial:
            event = {
                "type": "partial_transcript",
                "t_server_ms": now_ms(),
                "text": partial.text,
                "segment_id": f"{state.session_id}-{state.segment_index}",
                "stability_score": partial.stability,
            }
            events.append(event)
            self._log_event(state, event)
        segment_duration = concat_audio(state.buffer).size / state.sample_rate
        if segment_duration >= self.segment_seconds:
            segment = self._finalize_segment(state)
            event = {
                "type": "final_transcript",
                "t_server_ms": now_ms(),
                "text": state.pass1.finalize(segment.audio, state.sample_rate),
                "segment_id": segment.id,
            }
            events.append(event)
            self._log_event(state, event)
            self._save_transcript(state, segment.id, "pass1", event["text"])
            await self._refine_queue.put((state, segment))
        return events

    def finalize_session(self, state: SessionState) -> list[dict]:
        events: list[dict] = []
        if state.buffer:
            segment = self._finalize_segment(state, force=True)
            event = {
                "type": "final_transcript",
                "t_server_ms": now_ms(),
                "text": state.pass1.finalize(segment.audio, state.sample_rate),
                "segment_id": segment.id,
            }
            events.append(event)
            self._log_event(state, event)
            self._save_transcript(state, segment.id, "pass1", event["text"])
            asyncio.create_task(self._refine_queue.put((state, segment)))
        full_audio = concat_audio(state.full_audio)
        if full_audio.size:
            write_wav(state.artifacts_dir / "session.wav", full_audio, state.sample_rate)
        return events

    def _finalize_segment(self, state: SessionState, force: bool = False) -> SegmentInfo:
        audio = concat_audio(state.buffer)
        segment_id = f"{state.session_id}-{state.segment_index}"
        segment_path = state.artifacts_dir / f"segment_{state.segment_index}.wav"
        write_wav(segment_path, audio, state.sample_rate)
        start_ms = state.last_segment_start_ms
        end_ms = now_ms()
        segment = SegmentInfo(
            id=segment_id,
            start_ms=start_ms,
            end_ms=end_ms,
            audio=audio,
            audio_path=segment_path,
        )
        self.db_conn.execute(
            "INSERT INTO segments (id, session_id, start_ms, end_ms, audio_path) VALUES (?, ?, ?, ?, ?)",
            (segment.id, state.session_id, start_ms, end_ms, str(segment_path)),
        )
        self.db_conn.commit()
        overlap_samples = int(state.sample_rate * self.overlap_seconds)
        if not force and overlap_samples > 0 and audio.size > overlap_samples:
            state.buffer = [audio[-overlap_samples:]]
        else:
            state.buffer = []
        state.segment_index += 1
        state.last_segment_start_ms = now_ms()
        return segment

    async def _refine_worker(self) -> None:
        loop = asyncio.get_event_loop()
        while True:
            state, segment = await self._refine_queue.get()
            refined = await loop.run_in_executor(None, self.pass2.transcribe, segment.audio_path)
            event = {
                "type": "refined_transcript",
                "t_server_ms": now_ms(),
                "text": refined,
                "segment_id": segment.id,
                "pass2_backend": self.pass2.name,
            }
            self._log_event(state, event)
            self._save_transcript(state, segment.id, "pass2", refined)
            self._refine_queue.task_done()

    def _log_event(self, state: SessionState, event: dict) -> None:
        state.events.append(event)
        self.db_conn.execute(
            "INSERT INTO events (session_id, segment_id, event_type, t_ms, payload_json) VALUES (?, ?, ?, ?, ?)",
            (
                state.session_id,
                event.get("segment_id"),
                event["type"],
                event["t_server_ms"],
                str(event),
            ),
        )
        self.db_conn.commit()

    def _save_transcript(self, state: SessionState, segment_id: str, pass_name: str, text: str) -> None:
        self.db_conn.execute(
            "INSERT INTO transcripts (session_id, segment_id, pass, text, created_at_ms) VALUES (?, ?, ?, ?, ?)",
            (state.session_id, segment_id, pass_name, text, now_ms()),
        )
        self.db_conn.commit()
