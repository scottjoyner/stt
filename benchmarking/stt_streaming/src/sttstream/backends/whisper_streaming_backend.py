from __future__ import annotations

from sttstream.backends.faster_whisper_stream_backend import FasterWhisperStreamBackend


class WhisperStreamingBackend(FasterWhisperStreamBackend):
    """Compatibility wrapper for whisper_streaming-style backend.

    This uses the faster-whisper streaming implementation to provide
    partials and final transcripts without external APIs.
    """

    name = "whisper_streaming"
