from __future__ import annotations

import editdistance


def _tokenize(text: str) -> list[str]:
    return [t for t in text.strip().split() if t]


def wer(reference: str, hypothesis: str) -> float:
    ref_tokens = _tokenize(reference)
    hyp_tokens = _tokenize(hypothesis)
    if not ref_tokens:
        return 0.0 if not hyp_tokens else 1.0
    return editdistance.eval(ref_tokens, hyp_tokens) / max(len(ref_tokens), 1)


def cer(reference: str, hypothesis: str) -> float:
    ref = reference.strip()
    hyp = hypothesis.strip()
    if not ref:
        return 0.0 if not hyp else 1.0
    return editdistance.eval(ref, hyp) / max(len(ref), 1)
