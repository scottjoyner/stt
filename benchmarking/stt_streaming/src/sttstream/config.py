from dataclasses import dataclass
from pathlib import Path


@dataclass
class ServerConfig:
    host: str = "0.0.0.0"
    port: int = 8765
    segment_seconds: float = 4.0
    segment_overlap: float = 0.5
    sample_rate: int = 16000
    channels: int = 1
    artifacts_dir: Path = Path("runs")
    backend_pass1: str = "faster_whisper_stream"
    backend_pass2: str = "faster_whisper_batch"


@dataclass
class BackendConfig:
    model: str = "small"
    device: str = "cpu"
    compute_type: str = "int8"
    language: str | None = None
