from __future__ import annotations

import uuid


def new_segment_id() -> str:
    return str(uuid.uuid4())
