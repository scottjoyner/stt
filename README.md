# Realtime STT Service

Local-first Python realtime STT service (audio stream → VAD → segmenter → trigger/context → STT → speaker auth → event stream + JSONL persistence).

## Highlights (Event Contract v2)

- **Versioned event schema** (`schema_version: "2.0"`) shared across WebSocket and JSONL persistence.
- **Strong event metadata** on every event: `event_id`, `event_type`, `session_id`, `ts_wall`, `ts_mono_ms`, `source`.
- **Actionability signal** on `segment_final` for downstream Agent+TTS orchestrators.
- **Trigger command window** support (`trigger_context`) so follow-up segments stay command-aware.
- **Speaker auth quality signals** (`speaker_quality`) with short/noisy clipping safeguards.
- **Realtime partial transcript events** (`transcript_partial`) with bounded partial history.
- **Conversation grouping** (`conversation_start` / `conversation_end`) with rolling silence window.
- **Durable replay** via `GET /events/recent` and WS replay cursor (`from_event_id`).
- **Pipeline health** metrics via `GET /stats` and periodic `pipeline_health` events.

## API

- `GET /health`
- `GET /config`
- `GET /stats`
- `GET /events/recent?seconds=60`
- `WS /ws/events`
  - Optional first message:
    ```json
    {"op":"subscribe","from_event_id":"<event-id>"}
    ```

## Actionability rule

`actionability.is_actionable = true` when:

- `speaker.authenticated == true`
- and either trigger window is active (`trigger_context.triggered`) **or** rules intent class is actionable (`note|status|cancel`).

## Event examples

### `segment_final`

```json
{
  "schema_version": "2.0",
  "event_id": "27fcd896-d605-4d16-a9ce-194a0626d8e8",
  "event_type": "segment_final",
  "event": "segment_final",
  "session_id": "local",
  "ts_wall": "2026-02-11T12:00:00.000000+00:00",
  "ts_mono_ms": 333120,
  "source": "stt_service",
  "segment_id": "428dfab1-1ed4-4975-9f23-df41936f494b",
  "conversation_id": "1cdb8cf8-28ee-4adb-adf2-f9f969f4eb95",
  "duration_ms": 2460,
  "vad": {"speech_ratio": 0.91},
  "transcript_final": "computer create a note to call dan tomorrow",
  "trigger_context": {
    "triggered": true,
    "trigger_type": "phrase",
    "window_id": "64519c7e-70e8-4892-a218-fbc24d4b9a7e",
    "window_expires_ts": "2026-02-11T12:00:08.000000+00:00"
  },
  "speaker": {
    "user": "alice",
    "score": 0.83,
    "threshold": 0.55,
    "authenticated": true,
    "method": "ecapa",
    "embedding_id": "0d1b874e-80de-4ef5-8f4c-9f43fbeef9da"
  },
  "speaker_quality": {
    "duration_ms": 2460,
    "vad_ratio": 0.91,
    "snr_proxy": 12.3,
    "clipped": false,
    "quality": "good",
    "reason": "ok"
  },
  "actionability": {
    "is_actionable": true,
    "reason": "authenticated_and_triggered_or_intent",
    "confidence": 0.83
  }
}
```

### `transcript_partial`

```json
{
  "schema_version": "2.0",
  "event_id": "b0f7bde9-03a4-4cec-a5a0-c7002613ed88",
  "event_type": "transcript_partial",
  "session_id": "local",
  "ts_wall": "2026-02-11T12:00:00.100000+00:00",
  "ts_mono_ms": 331100,
  "source": "stt_service",
  "segment_id": "428dfab1-1ed4-4975-9f23-df41936f494b",
  "conversation_id": "1cdb8cf8-28ee-4adb-adf2-f9f969f4eb95",
  "partial_text": "computer create a note",
  "stable_text": "computer create a note",
  "progress": 0.9,
  "chunk_idx": 7
}
```

### `conversation_start` / `conversation_end`

```json
{
  "schema_version": "2.0",
  "event_id": "0b718dd1-f4ed-4cd9-b915-cf6a6c4f5900",
  "event_type": "conversation_start",
  "session_id": "local",
  "ts_wall": "2026-02-11T12:00:00.000000+00:00",
  "ts_mono_ms": 320000,
  "source": "stt_service",
  "conversation_id": "1cdb8cf8-28ee-4adb-adf2-f9f969f4eb95"
}
```

```json
{
  "schema_version": "2.0",
  "event_id": "6efee253-cf3c-4adf-a67d-2f96e95efbd8",
  "event_type": "conversation_end",
  "session_id": "local",
  "ts_wall": "2026-02-11T12:01:05.000000+00:00",
  "ts_mono_ms": 385000,
  "source": "stt_service",
  "conversation_id": "1cdb8cf8-28ee-4adb-adf2-f9f969f4eb95"
}
```

### `pipeline_health`

```json
{
  "schema_version": "2.0",
  "event_id": "9d7e3ecd-8f42-43f2-80a3-a627894c96f2",
  "event_type": "pipeline_health",
  "session_id": "local",
  "ts_wall": "2026-02-11T12:00:05.000000+00:00",
  "ts_mono_ms": 325000,
  "source": "stt_service",
  "audio_queue_depth": 2,
  "vad_latency_ms": 0.4,
  "stt_processing_ms_avg": 76.2,
  "dropped_frames": 0
}
```

## Downstream Agent+TTS integration

Consume `/ws/events`, filter to `segment_final` where:

- `speaker.authenticated == true`
- `actionability.is_actionable == true`

Use `conversation_id` + `segment_id` for context stitching and `from_event_id` replay on reconnect.

## Notes

- Local-first: no cloud dependencies required.
- Single-speaker-per-segment auth model (no full diarization).
- Trigger and actionability use rules-first logic; optional LLM hook can be added behind `intent_llm_enabled`.
