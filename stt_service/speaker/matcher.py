from __future__ import annotations

import numpy as np

from stt_service.speaker.voiceprints import Voiceprint


class SpeakerMatcher:
    def __init__(self, threshold: float) -> None:
        self.threshold = threshold

    def match(self, embedding: np.ndarray, voiceprints: list[Voiceprint]) -> tuple[str | None, float, bool, float]:
        if not voiceprints:
            return None, 0.0, False, self.threshold
        scores = []
        for vp in voiceprints:
            score = float(np.dot(embedding, vp.embedding) / ((np.linalg.norm(embedding) * np.linalg.norm(vp.embedding)) + 1e-9))
            scores.append((vp.user, score, vp.auth_threshold))
        best_user, best_score, best_threshold = max(scores, key=lambda item: item[1])
        threshold = best_threshold or self.threshold
        return best_user, best_score, best_score >= threshold, threshold
