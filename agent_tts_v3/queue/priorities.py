from __future__ import annotations

PRIORITY_ORDER = {"critical": 0, "interactive": 1, "background": 2}


def sort_key(priority: str) -> int:
    return PRIORITY_ORDER.get(priority, 9)
