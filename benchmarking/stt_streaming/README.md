# stt_streaming

Minimal local streaming STT + dual-pass refinement + benchmarking.

## Quickstart

```bash
cd benchmarking/stt_streaming
python -m venv .venv
source .venv/bin/activate
pip install -e .
# Optional for real ASR backends
pip install -e ".[whisper]"

# Generate sample audio (binary files are not stored in the repo)
python scripts/generate_sample.py --wav tests/fixtures/sample.wav --text tests/fixtures/sample.txt
python scripts/generate_sample.py --wav dataset/sample.wav --text dataset/sample.txt

# Run server
sttstream serve --host 0.0.0.0 --port 8765 --backend-pass1 faster_whisper_stream --backend-pass2 faster_whisper_batch

# Replay a WAV (deterministic, real-time) + optional transcript scoring
sttstream replay --url ws://localhost:8765/ws --wav tests/fixtures/sample.wav --text tests/fixtures/sample.txt

# Benchmark dataset
sttstream bench --dataset dataset/manifest.jsonl --configs configs/bench.yaml --out runs/demo

# Export report
sttstream export-report --run runs/demo/results.sqlite
```
