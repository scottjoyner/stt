from __future__ import annotations

from pathlib import Path

from sttstream.backends.base import BatchBackend


class VibeVoiceASRStub(BatchBackend):
    """Stub backend for VibeVoice-ASR.

    TODO:
      - Install VibeVoice + VibeVoice-ASR per https://github.com/microsoft/VibeVoice
      - Replace this stub with a real call into the model.
    """

    name = "vibevoice_asr_stub"

    def transcribe(self, audio_path: Path) -> str:
        return "[vibevoice stub: not implemented]"
