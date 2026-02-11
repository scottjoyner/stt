from __future__ import annotations

import numpy as np

from stt_service.speaker.matcher import SpeakerMatcher
from stt_service.speaker.voiceprints import Voiceprint


def test_matcher_selects_best_voiceprint() -> None:
    matcher = SpeakerMatcher(threshold=0.5)
    vp1 = Voiceprint("alice", np.array([1.0, 0.0], dtype=np.float32), 3, "m", "now")
    vp2 = Voiceprint("bob", np.array([0.0, 1.0], dtype=np.float32), 3, "m", "now")
    user, score, auth = matcher.match(np.array([0.9, 0.1], dtype=np.float32), [vp1, vp2])
    assert user == "alice"
    assert score > 0.8
    assert auth is True
