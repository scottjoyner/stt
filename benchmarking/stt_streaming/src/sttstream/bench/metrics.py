from __future__ import annotations

from dataclasses import dataclass

from sttstream.util.wer import cer, wer


@dataclass
class SegmentMetrics:
    ttft_ms: float
    ttfinal_ms: float
    ttrefine_ms: float
    churn: float
    wer_final: float
    wer_refined: float
    cer_final: float
    cer_refined: float


def compute_metrics(reference: str, final_text: str, refined_text: str, partials: list[str], ttft_ms: float, ttfinal_ms: float, ttrefine_ms: float) -> SegmentMetrics:
    churn = 0.0
    if len(partials) > 1:
        total = 0.0
        for a, b in zip(partials, partials[1:]):
            total += cer(a, b)
        churn = total / max(len(partials) - 1, 1)
    return SegmentMetrics(
        ttft_ms=ttft_ms,
        ttfinal_ms=ttfinal_ms,
        ttrefine_ms=ttrefine_ms,
        churn=churn,
        wer_final=wer(reference, final_text),
        wer_refined=wer(reference, refined_text),
        cer_final=cer(reference, final_text),
        cer_refined=cer(reference, refined_text),
    )
