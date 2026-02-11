# Realtime STT Service

Local-first Python service for realtime speech transcription with VAD segmentation, trigger phrase handling, and optional voice fingerprint authentication.

## Features

- Realtime microphone ingestion (`sounddevice`) with bounded queue/ring buffer.
- VAD-driven segmentation (default energy VAD, swappable interface).
- Streaming-like STT via chunked `faster-whisper` transcriber (fallback stub if model missing).
- Trigger phrase detector (`hey assistant`, `computer`, `ok ralph`) + command routing.
- Voice fingerprint enrollment and matching with `speechbrain` (fallback deterministic embedding if unavailable).
- JSONL append-only event persistence and optional WAV segment persistence.
- FastAPI endpoints + WebSocket event stream.

## Quickstart

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .[dev]
# optional full ML stack:
# pip install -e .[ml,dev]

stt run
```

## CLI

- `stt run` — runs realtime microphone pipeline.
- `stt serve` — starts FastAPI server (`/health`, `/config`, `/ws/events`).
- `stt enroll --user alice` — enrollment wizard from sentence prompts.
- `stt list-voiceprints` — list enrolled identities.
- `stt test-file --path audio.wav` — process a 16k mono WAV through the pipeline.

## VAD + Segmenting behavior

Pipeline:

`Audio Ingest -> Preprocess -> VAD -> Segmenter -> Trigger -> STT -> Persist -> EventBus`

Segmenter behavior:

- Pre-roll buffer (`vad_preroll_ms`) avoids clipped speech start.
- Enforces minimum speech duration (`vad_min_speech_ms`).
- Ends segment after silence threshold (`VAD_SILENCE_MS`).
- Emits `speech_start` and `speech_end` events with monotonic timestamps.

## Enrollment and authentication

1. Run: `stt enroll --user alice`
2. Read the prompted sentences, supplying path to each recorded 16k WAV.
3. Service averages normalized segment embeddings into one stable voiceprint.
4. Voiceprint saved to `data/voiceprints/<user>.json`.
5. During normal operation, each completed segment gets matched with cosine similarity against all stored voiceprints:
   - `authenticated=true` when similarity >= `AUTH_THRESHOLD`
   - otherwise speaker is `unknown`

> Calibration: start with `AUTH_THRESHOLD=0.55`, then tune based on false accepts/rejects for your microphone room conditions.

## Config reference

Environment variables (or JSON/YAML via `--config`):

- `STT_SAMPLE_RATE` (default `16000`)
- `VAD_MODE` (default `energy`)
- `VAD_SILENCE_MS` (default `900`)
- `STT_MODEL` (default `base`)
- `TRIGGER_PHRASES` (list; default wake phrases in config)
- `AUTH_THRESHOLD` (default `0.55`)
- `DATA_DIR` (default `data`)

## Storage layout

- Events JSONL: `data/events/YYYY/MM/DD/session_<id>.jsonl`
- Optional segment WAVs: `data/audio/YYYY/MM/DD/<segment_id>.wav`
- Voiceprints: `data/voiceprints/<user>.json`
- Enrollment assets (optional): `data/enrollments/`

## Extending wake-word detection later

Current wake-word detector is a stub (`WakeWordStubDetector`).
To integrate a real engine later:

1. Implement a new `TriggerDetector` that consumes frame-level audio.
2. Run detector continuously during active stream (not only after transcript partials).
3. Emit precise `trigger_offset_ms` from engine timestamps.
4. Swap implementation in `RuntimePipeline` while preserving the trigger interface.

