# Realtime + Batch Speech-to-Text Benchmarking

This folder captures a local/on‑prem benchmarking plan for dual‑inference speech‑to‑text (STT):

1. **Realtime pass** for lowest possible latency.
2. **Follow‑up pass** on the saved audio for higher accuracy.

The goal is to compare multiple approaches (Whisper variants, streaming engines, and other ASR models) while preserving audio and transcripts so that downstream LLM + TTS can be evaluated later.

## Objectives

- **Minimize end‑to‑end latency** from microphone input to partial transcript.
- **Maintain a high‑quality second pass** with improved transcript accuracy.
- **Persist raw audio and intermediate artifacts** for reproducibility.
- **Keep everything local/on‑prem**, with modular runtimes (CPU/GPU/MLX/ONNX/CUDA).

## Candidate Models & Systems

### Realtime / Low‑latency Focus
- **whisper_streaming** (ufal/whisper_streaming): streaming whisper with chunked/online decoding. Good for low latency and partials.
- **faster‑whisper** with runtime auto‑selection (CUDA/CPU/MLX/ONNX), using a small or turbo variant for speed.
- **VibeVoice realtime** (microsoft/VibeVoice, realtime branch) for streaming ASR experimentation.

### Quality‑focused Second Pass
- **openai/whisper-large-v3-turbo** or **whisper-large‑v3** for high quality batch inference.
- **Alternate top leaderboard models** (per HF open_asr_leaderboard) that can run locally.

## Architecture Overview

```
[Audio Source]
     | (streamed PCM frames)
     v
[Realtime STT]
     | (partial + final transcript)
     | (latency metrics)
     +------> [Artifact Store]
     |                 |
     |                 +--> raw audio (wav/flac)
     |                 +--> realtime transcript
     |                 +--> segmentation metadata
     v
[Batch STT (second pass)]
     | (improved transcript)
     +------> [Artifact Store]
                       +--> batch transcript + alignment
```

**Key principle:** Always save the raw audio and segmentation info so the batch model can run later without loss.

## Data Flow & Artifacts

**Artifact store layout (suggested):**

```
benchmarking/
  runs/
    <run-id>/
      audio/
        input.wav
      realtime/
        transcript.jsonl
        metrics.json
      batch/
        transcript.jsonl
        metrics.json
      meta.json
```

- **`meta.json`**: model versions, runtime settings, chunk sizes, device info.
- **`metrics.json`**: latency stats, token latency, audio -> text timings.
- **`transcript.jsonl`**: incremental and final segments, with timestamps.

## Benchmark Phases

1. **Streaming phase**
   - Capture audio in small frames (e.g., 20–40ms).
   - Feed to streaming ASR, emit partials & finals.
   - Record partial latency and finalization time.

2. **Batch phase**
   - Run a higher‑quality model on the saved full audio.
   - Record quality metrics (WER/CER) when reference is available.

## Metrics to Capture

### Latency
- **Input‑to‑partial** (ms)
- **Input‑to‑final** (ms)
- **Chunk processing time** (ms)
- **CPU/GPU utilization**

### Accuracy
- **WER/CER** vs reference (if available)
- **Segment‑level confidence**

### Resource & Cost
- Peak VRAM/RAM usage
- Model load time
- Throughput (x realtime)

## Implementation Notes

- **Audio format**: 16‑bit PCM, 16kHz or 48kHz depending on model.
- **Chunk size**: start with 200–500ms for realtime, adjust for latency/quality balance.
- **Silence/VAD**: optional VAD to cut segments (try WebRTC VAD or Silero VAD).
- **Runtime selection**: allow runtime fallback (CUDA -> MPS/MLX -> CPU).

## Suggested Experiments

1. **Whisper streaming baseline**
   - whisper_streaming + small/turbo model
   - measure partial/final latency

2. **Faster‑whisper runtime sweep**
   - CPU vs CUDA vs MLX (if available)
   - compare realtime factor and WER

3. **VibeVoice realtime**
   - measure streaming behavior and compare to whisper streaming

4. **High quality pass**
   - whisper-large‑v3‑turbo as batch
   - compare deltas vs realtime transcripts

## Next Steps (for TTS/LLM integration)

- Add an LLM post‑processor to clean transcript or summarize.
- Add TTS benchmarking (latency and quality) after STT is stable.

## References

- HF Open ASR Leaderboard: https://huggingface.co/spaces/hf-audio/open_asr_leaderboard
- VibeVoice: https://github.com/microsoft/VibeVoice/tree/main
- whisper_streaming: https://github.com/ufal/whisper_streaming
- whisper-large-v3-turbo: https://huggingface.co/openai/whisper-large-v3-turbo
