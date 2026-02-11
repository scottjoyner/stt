from __future__ import annotations

import numpy as np


def estimate_snr_proxy(samples: np.ndarray) -> float:
    if samples.size == 0:
        return 0.0
    peak = float(np.max(np.abs(samples))) + 1e-6
    rms = float(np.sqrt(np.mean(np.square(samples)))) + 1e-6
    return max(0.0, min(60.0, 20.0 * np.log10(peak / rms)))


def detect_clipping(samples: np.ndarray, threshold: float = 0.98) -> bool:
    if samples.size == 0:
        return False
    return bool(np.any(np.abs(samples) >= threshold))


def speaker_quality(samples: np.ndarray, sample_rate: int, speech_ratio: float) -> dict[str, object]:
    duration_ms = int((len(samples) / sample_rate) * 1000)
    snr = estimate_snr_proxy(samples)
    clipped = detect_clipping(samples)
    quality = "good"
    reason = "ok"
    if duration_ms < 1200:
        quality = "poor"
        reason = "too_short"
    elif snr < 6.0:
        quality = "poor"
        reason = "too_noisy"
    elif clipped:
        quality = "poor"
        reason = "clipped"
    return {
        "duration_ms": duration_ms,
        "vad_ratio": speech_ratio,
        "snr_proxy": round(float(snr), 3),
        "clipped": clipped,
        "quality": quality,
        "reason": reason,
    }
