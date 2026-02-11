#!/usr/bin/env bash
set -euo pipefail

python - <<'PY'
print('Install optional models with: pip install "realtime-stt-service[ml]"')
print('Then run once: python -c "from faster_whisper import WhisperModel; WhisperModel(\"base\")"')
print('Speaker model downloads on first enrollment/auth use via speechbrain.')
PY
