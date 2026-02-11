from __future__ import annotations

import re


class CommandRouter:
    def parse_intent(self, text: str) -> dict[str, str]:
        text = text.lower()
        if re.search(r"\b(stop|cancel)\b", text):
            return {"intent": "cancel"}
        if re.search(r"\b(status|health)\b", text):
            return {"intent": "status"}
        if re.search(r"\b(note|remember)\b", text):
            return {"intent": "note"}
        return {"intent": "unknown"}
