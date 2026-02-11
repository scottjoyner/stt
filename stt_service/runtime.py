from __future__ import annotations

import asyncio
import logging
import queue
from collections import deque
from dataclasses import dataclass, field

import numpy as np

from stt_service.audio.input import AudioFrame, MicrophoneInput
from stt_service.audio.ring_buffer import AudioRingBuffer
from stt_service.config import Settings
from stt_service.conversation.grouping import ConversationGroup
from stt_service.events.bus import EventBus
from stt_service.events.schema import SCHEMA_VERSION
from stt_service.speaker.embedder import SpeakerEmbedder
from stt_service.speaker.matcher import SpeakerMatcher
from stt_service.speaker.quality import speaker_quality
from stt_service.speaker.voiceprints import VoiceprintStore
from stt_service.storage.jsonl import JsonlEventWriter
from stt_service.storage.wav import SegmentWavWriter
from stt_service.stt.base import TranscriptChunk
from stt_service.stt.faster_whisper_transcriber import FasterWhisperTranscriber
from stt_service.trigger.commands import CommandRouter
from stt_service.trigger.phrase import TriggerPhraseDetector
from stt_service.trigger.window import TriggerWindowState
from stt_service.utils.ids import new_event_id, new_segment_id
from stt_service.utils.time import now_monotonic, now_wall_iso
from stt_service.vad.energy_vad import EnergyVAD
from stt_service.vad.segmenter import Segmenter
from voicebus.tracing.trace import new_trace

LOGGER = logging.getLogger(__name__)


@dataclass
class RuntimePipeline:
    settings: Settings
    bus: EventBus
    frame_queue: queue.Queue[AudioFrame] = field(init=False)

    def __post_init__(self) -> None:
        self.frame_queue = queue.Queue(maxsize=self.settings.queue_maxsize)
        ring = AudioRingBuffer(max_samples=self.settings.sample_rate * self.settings.ring_buffer_seconds)
        self.segmenter = Segmenter(settings=self.settings, vad=EnergyVAD(self.settings.vad_energy_threshold), ring=ring)
        self.transcriber = FasterWhisperTranscriber(self.settings.stt_model)
        self.trigger = TriggerPhraseDetector(self.settings.trigger_phrases)
        self.trigger_window = TriggerWindowState(self.settings.trigger_window_seconds)
        self.router = CommandRouter()
        self.embedder = SpeakerEmbedder(self.settings.speaker_model)
        self.matcher = SpeakerMatcher(self.settings.auth_threshold)
        self.voiceprints = VoiceprintStore(self.settings.data_dir / "voiceprints")
        self.events = JsonlEventWriter(self.settings.data_dir, self.settings.session_id)
        self.wav_writer = SegmentWavWriter(self.settings.data_dir, self.settings.sample_rate)
        self.mic = MicrophoneInput(self.settings, self.frame_queue)
        self.conversations = ConversationGroup(self.settings.conversation_silence_seconds)
        self._partial_history: deque[str] = deque(maxlen=20)
        self._stt_times_ms: deque[float] = deque(maxlen=50)
        self._vad_latency_ms: float = 0.0
        self._last_health_ts = 0.0

    async def run_microphone(self) -> None:
        self.mic.start()
        try:
            while True:
                frame = await asyncio.to_thread(self.frame_queue.get)
                await self.handle_frame(frame)
        finally:
            self.mic.stop()

    async def handle_frame(self, frame: AudioFrame) -> None:
        t0 = now_monotonic()
        events, completed = self.segmenter.push(frame.samples, frame.monotonic_ts)
        self._vad_latency_ms = max(0.0, (now_monotonic() - t0) * 1000)

        for event in events:
            if event["type"] == "speech_start":
                started, ended = self.conversations.on_segment_start(event["mono_ts"])
                if ended:
                    await self._emit_generic("conversation_end", {"conversation_id": ended}, event["mono_ts"])
                if started:
                    await self._emit_generic("conversation_start", {"conversation_id": started}, event["mono_ts"])
            await self.bus.publish(event["type"], event)

        for seg in completed:
            self.conversations.touch(seg.end_mono)
            await self._handle_segment(seg)

        await self._emit_health_if_due(frame.monotonic_ts)

    async def _handle_segment(self, seg) -> None:
        segment_id = new_segment_id()
        turn_id = f"turn_{segment_id}"
        trace = new_trace()
        t0 = now_monotonic()
        partial = self.transcriber.partial(seg.samples, self.settings.sample_rate)
        final = self.transcriber.final(seg.samples, self.settings.sample_rate)
        self._stt_times_ms.append((now_monotonic() - t0) * 1000)

        duration_ms = int(1000 * len(seg.samples) / self.settings.sample_rate)
        trig_partial = self.trigger.evaluate_text(partial.text)
        trig_final = self.trigger.evaluate_text(final.text)
        if trig_partial.triggered or trig_final.triggered:
            self.trigger_window.open(seg.end_mono, (trig_final.trigger_type or trig_partial.trigger_type or "phrase"))
        trigger_ctx = self.trigger_window.context(seg.end_mono)
        trigger_ctx["window_expires_ts"] = now_wall_iso() if trigger_ctx["triggered"] else None

        voiceprints = self.voiceprints.load_all()
        emb = self.embedder.embed(seg.samples, self.settings.sample_rate)
        embedding_id = new_event_id()
        sp_quality = speaker_quality(seg.samples, self.settings.sample_rate, seg.speech_ratio)

        if duration_ms < self.settings.auth_min_duration_ms:
            user, score, auth, threshold = None, 0.0, False, self.settings.auth_threshold
            speaker_reason = "segment_too_short"
        else:
            user, score, auth, threshold = self.matcher.match(emb, voiceprints)
            speaker_reason = "matched" if auth else "below_threshold"

        intent = self.router.parse_intent(final.text)
        actionable = auth and (bool(trigger_ctx["triggered"]) or intent.get("intent") in {"note", "status", "cancel"})
        reason = "authenticated_and_triggered_or_intent" if actionable else "missing_auth_or_command_signal"
        conv_id = self.conversations.current()

        await self._emit_turn_event("turn_start", turn_id, conv_id, partial.text, seg.start_mono, trace.trace_id, trace.span_id)
        if partial.text.strip():
            await self._emit_turn_event("turn_update", turn_id, conv_id, partial.text, seg.end_mono, trace.trace_id, trace.span_id)
        await self._emit_turn_event("turn_final", turn_id, conv_id, final.text, seg.end_mono, trace.trace_id, trace.span_id)

        payload = {
            "schema_version": SCHEMA_VERSION,
            "event_id": new_event_id(),
            "event_type": "segment_final",
            "session_id": self.settings.session_id,
            "ts_wall": now_wall_iso(),
            "ts_mono_ms": int(seg.end_mono * 1000),
            "source": "stt_service",
            "trace_id": trace.trace_id,
            "span_id": trace.child().span_id,
            "segment_id": segment_id,
            "turn_id": turn_id,
            "conversation_id": conv_id,
            "start_mono_ms": int(seg.start_mono * 1000),
            "end_mono_ms": int(seg.end_mono * 1000),
            "duration_ms": duration_ms,
            "vad": {"speech_ratio": seg.speech_ratio},
            "trigger_context": trigger_ctx,
            "transcript_final": final.text,
            "speaker": {
                "user": user,
                "score": float(score),
                "threshold": float(threshold),
                "authenticated": bool(auth),
                "method": "ecapa",
                "embedding_id": embedding_id,
                "reason": speaker_reason,
            },
            "speaker_quality": sp_quality,
            "actionability": {
                "is_actionable": actionable,
                "reason": reason,
                "confidence": round(max(0.0, min(1.0, float(score))), 4),
            },
        }

        validated = self.events.append(payload)
        if self.settings.save_segment_wav:
            self.wav_writer.save(segment_id, seg.samples)

        if self.settings.partials_enabled:
            await self._emit_partial(segment_id, turn_id, trace.trace_id, seg, partial)

        LOGGER.info(
            "segment_processed segment_id=%s dur_ms=%s stt_ms=%.2f auth=%s score=%.3f actionable=%s",
            segment_id,
            duration_ms,
            self._stt_times_ms[-1] if self._stt_times_ms else 0.0,
            auth,
            score,
            actionable,
        )
        await self.bus.publish("segment_final", validated)

        if trig_final.triggered:
            await self.bus.publish("command_final", {"segment_id": segment_id, "text": final.text, "intent": intent})

    async def _emit_partial(self, segment_id: str, turn_id: str, trace_id: str, seg, partial: TranscriptChunk) -> None:
        text = partial.text.strip()
        self._partial_history.append(text)
        payload = {
            "schema_version": SCHEMA_VERSION,
            "event_id": new_event_id(),
            "event_type": "transcript_partial",
            "session_id": self.settings.session_id,
            "ts_wall": now_wall_iso(),
            "ts_mono_ms": int(seg.end_mono * 1000),
            "source": "stt_service",
            "trace_id": trace_id,
            "segment_id": segment_id,
            "turn_id": turn_id,
            "conversation_id": self.conversations.current(),
            "partial_text": text,
            "stable_text": text,
            "progress": 0.9,
            "chunk_idx": len(self._partial_history),
        }
        validated = self.events.append(payload)
        await self.bus.publish("transcript_partial", validated)

    async def _emit_generic(self, event_type: str, extra: dict, mono_ts: float) -> None:
        payload = {
            "schema_version": SCHEMA_VERSION,
            "event_id": new_event_id(),
            "event_type": event_type,
            "session_id": self.settings.session_id,
            "ts_wall": now_wall_iso(),
            "ts_mono_ms": int(mono_ts * 1000),
            "source": "stt_service",
            **extra,
        }
        validated = self.events.append(payload)
        await self.bus.publish(event_type, validated)

    async def _emit_turn_event(
        self,
        event_type: str,
        turn_id: str,
        conversation_id: str | None,
        text: str,
        mono_ts: float,
        trace_id: str,
        span_id: str,
    ) -> None:
        if conversation_id is None:
            return
        payload = {
            "schema_version": SCHEMA_VERSION,
            "event_id": new_event_id(),
            "event_type": event_type,
            "session_id": self.settings.session_id,
            "ts_wall": now_wall_iso(),
            "ts_mono_ms": int(mono_ts * 1000),
            "source": "stt_service",
            "conversation_id": conversation_id,
            "turn_id": turn_id,
            "trace_id": trace_id,
            "span_id": span_id,
            "transcript_text": text.strip(),
        }
        validated = self.events.append(payload)
        await self.bus.publish(event_type, validated)

    async def _emit_health_if_due(self, mono_ts: float) -> None:
        if (mono_ts - self._last_health_ts) < self.settings.pipeline_health_interval_seconds:
            return
        self._last_health_ts = mono_ts
        avg_stt = float(np.mean(self._stt_times_ms)) if self._stt_times_ms else 0.0
        payload = {
            "schema_version": SCHEMA_VERSION,
            "event_id": new_event_id(),
            "event_type": "pipeline_health",
            "session_id": self.settings.session_id,
            "ts_wall": now_wall_iso(),
            "ts_mono_ms": int(mono_ts * 1000),
            "source": "stt_service",
            "audio_queue_depth": self.frame_queue.qsize(),
            "vad_latency_ms": round(self._vad_latency_ms, 3),
            "stt_processing_ms_avg": round(avg_stt, 3),
            "dropped_frames": self.mic.dropped_frames,
        }
        validated = self.events.append(payload)
        await self.bus.publish("pipeline_health", validated)

    def stats(self) -> dict[str, float | int | str]:
        avg_stt = float(np.mean(self._stt_times_ms)) if self._stt_times_ms else 0.0
        return {
            "schema_version": SCHEMA_VERSION,
            "session_id": self.settings.session_id,
            "audio_queue_depth": self.frame_queue.qsize(),
            "vad_latency_ms": round(self._vad_latency_ms, 3),
            "stt_processing_ms_avg": round(avg_stt, 3),
            "dropped_frames": self.mic.dropped_frames,
        }
