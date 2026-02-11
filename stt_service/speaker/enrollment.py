from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from stt_service.speaker.embedder import SpeakerEmbedder
from stt_service.speaker.voiceprints import Voiceprint
from stt_service.utils.time import now_wall_iso

ENROLLMENT_SENTENCES = [
    "Today I am enrolling my voice for the local speech system.",
    "The quick brown fox jumps over the lazy dog.",
    "Please verify this speaker profile with confidence.",
    "I use this assistant for notes and reminders.",
    "Real time speech transcription helps me work faster.",
    "Security matters when handling voice commands.",
]


@dataclass(slots=True)
class EnrollmentResult:
    voiceprint: Voiceprint


class EnrollmentService:
    def __init__(self, embedder: SpeakerEmbedder, model_version: str) -> None:
        self.embedder = embedder
        self.model_version = model_version

    def build_voiceprint(self, user: str, segments: list[np.ndarray], sample_rate: int) -> EnrollmentResult:
        if not segments:
            raise ValueError("No enrollment segments captured")
        embs = [self.embedder.embed(seg, sample_rate) for seg in segments]
        mean = np.mean(np.stack(embs), axis=0)
        mean = mean / (np.linalg.norm(mean) + 1e-9)
        vp = Voiceprint(
            user=user,
            embedding=mean.astype(np.float32),
            sample_count=len(segments),
            model_version=self.model_version,
            created_at=now_wall_iso(),
        )
        return EnrollmentResult(voiceprint=vp)
