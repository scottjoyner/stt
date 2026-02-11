from __future__ import annotations

import hashlib

import numpy as np

try:
    from speechbrain.inference.speaker import EncoderClassifier
except Exception:  # pragma: no cover
    EncoderClassifier = None


class SpeakerEmbedder:
    def __init__(self, model_id: str) -> None:
        self._classifier = EncoderClassifier.from_hparams(source=model_id) if EncoderClassifier else None

    def embed(self, audio: np.ndarray, sample_rate: int) -> np.ndarray:
        if self._classifier is None:
            # deterministic fallback embedding from signal bytes
            digest = hashlib.sha256(audio.tobytes()).digest()
            vec = np.frombuffer(digest * 8, dtype=np.uint8).astype(np.float32)[:192]
            vec = (vec - vec.mean()) / (vec.std() + 1e-6)
            return vec / (np.linalg.norm(vec) + 1e-9)

        import torch

        tensor = torch.from_numpy(audio).unsqueeze(0)
        emb = self._classifier.encode_batch(tensor).squeeze().detach().cpu().numpy()
        emb = emb.astype(np.float32)
        return emb / (np.linalg.norm(emb) + 1e-9)
