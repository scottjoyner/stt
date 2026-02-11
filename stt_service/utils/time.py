from __future__ import annotations

import time
from datetime import datetime, timezone


def now_wall_iso() -> str:
    return datetime.now(tz=timezone.utc).isoformat()


def now_monotonic() -> float:
    return time.monotonic()
