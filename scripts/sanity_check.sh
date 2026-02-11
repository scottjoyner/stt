#!/usr/bin/env bash
set -euo pipefail
python -m stt_service.main --help
python -m pytest -q
