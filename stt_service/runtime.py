from __future__ import annotations

import asyncio
import logging
import queue
from dataclasses import dataclass, field

import numpy as np

from stt_service.audio.input import AudioFrame, MicrophoneInput
from stt_service.audio.ring_buffer import AudioRingBuffer
from stt_service.config import Settings
from stt_service.events.bus import EventBus
from stt_service.speaker.embedder import SpeakerEmbedder
from stt_service.speaker.matcher import SpeakerMatcher
from stt_service.speaker.voiceprints import VoiceprintStore
from stt_service.storage.jsonl import JsonlEventWriter
from stt_service.storage.wav import SegmentWavWriter
from stt_service.stt.base import TranscriptChunk
from stt_service.stt.faster_whisper_transcriber import FasterWhisperTranscriber
from stt_service.trigger.commands import CommandRouter
from stt_service.trigger.phrase import TriggerPhraseDetector
from stt_service.utils.ids import new_segment_id
from stt_service.utils.time import now_wall_iso
from stt_service.vad.energy_vad import EnergyVAD
from stt_service.vad.segmenter import Segmenter

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
        self.router = CommandRouter()
        self.embedder = SpeakerEmbedder(self.settings.speaker_model)
        self.matcher = SpeakerMatcher(self.settings.auth_threshold)
        self.voiceprints = VoiceprintStore(self.settings.data_dir / "voiceprints")
        self.events = JsonlEventWriter(self.settings.data_dir, self.settings.session_id)
        self.wav_writer = SegmentWavWriter(self.settings.data_dir, self.settings.sample_rate)
        self.mic = MicrophoneInput(self.settings, self.frame_queue)

    async def run_microphone(self) -> None:
        self.mic.start()
        try:
            while True:
                frame = await asyncio.to_thread(self.frame_queue.get)
                await self.handle_frame(frame)
        finally:
            self.mic.stop()

    async def handle_frame(self, frame: AudioFrame) -> None:
        events, completed = self.segmenter.push(frame.samples, frame.monotonic_ts)
        for event in events:
            await self.bus.publish(event["type"], event)

        for seg in completed:
            segment_id = new_segment_id()
            partial = self.transcriber.partial(seg.samples, self.settings.sample_rate)
            final = self.transcriber.final(seg.samples, self.settings.sample_rate)
            trigger_res = self.trigger.evaluate_text(partial.text)
            voiceprints = self.voiceprints.load_all()
            emb = self.embedder.embed(seg.samples, self.settings.sample_rate)
            candidate, score, auth = self.matcher.match(emb, voiceprints)

            payload = self._build_segment_payload(segment_id, seg.start_mono, seg.end_mono, seg.samples, seg.speech_ratio, partial, final, trigger_res.triggered, candidate, score, auth)
            self.events.append(payload)
            if self.settings.save_segment_wav:
                self.wav_writer.save(segment_id, seg.samples)

            await self.bus.publish("transcript_partial", {"segment_id": segment_id, "text": partial.text})
            await self.bus.publish("transcript_final", payload)

            if trigger_res.triggered:
                intent = self.router.parse_intent(final.text)
                await self.bus.publish("command_final", {"segment_id": segment_id, "text": final.text, "intent": intent})

    def _build_segment_payload(
        self,
        segment_id: str,
        start_mono: float,
        end_mono: float,
        samples: np.ndarray,
        speech_ratio: float,
        partial: TranscriptChunk,
        final: TranscriptChunk,
        triggered: bool,
        candidate: str,
        score: float,
        auth: bool,
    ) -> dict:
        return {
            "event": "segment_final",
            "segment_id": segment_id,
            "start_ts": {"wall": now_wall_iso(), "monotonic": start_mono},
            "end_ts": {"wall": now_wall_iso(), "monotonic": end_mono},
            "audio_format": "pcm_f32le",
            "sample_rate": self.settings.sample_rate,
            "duration_ms": int(1000 * len(samples) / self.settings.sample_rate),
            "vad": {"speech_ratio": speech_ratio},
            "trigger": {
                "triggered": triggered,
                "trigger_type": "phrase" if triggered else None,
                "trigger_offset_ms": 0 if triggered else None,
            },
            "transcript_final": final.text,
            "transcript_partials": [partial.text][-5:],
            "speaker": {
                "speaker_candidate": candidate,
                "speaker_score": score,
                "authenticated": auth,
            },
        }
