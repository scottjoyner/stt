from __future__ import annotations

import hashlib


def task_signature(turn_id: str, intent: str, details: str) -> str:
    raw = f"{turn_id}|{intent}|{details}".encode("utf-8")
    return hashlib.sha256(raw).hexdigest()[:16]
