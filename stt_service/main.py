from __future__ import annotations

import argparse
import asyncio
import logging
from pathlib import Path

import numpy as np
import uvicorn

from stt_service.audio.file_source import read_wav_mono_16k
from stt_service.audio.input import AudioFrame
from stt_service.config import Settings, ensure_data_dirs
from stt_service.events.api import build_app
from stt_service.events.bus import EventBus
from stt_service.runtime import RuntimePipeline
from stt_service.speaker.enrollment import ENROLLMENT_SENTENCES, EnrollmentService
from stt_service.speaker.embedder import SpeakerEmbedder
from stt_service.speaker.voiceprints import VoiceprintStore
from stt_service.utils.logging import configure_logging
from stt_service.utils.time import now_monotonic

LOGGER = logging.getLogger(__name__)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser("stt")
    parser.add_argument("--config", type=Path, default=None)
    sub = parser.add_subparsers(dest="cmd", required=True)

    sub.add_parser("run", help="Run realtime microphone pipeline")
    sub.add_parser("serve", help="Run FastAPI server only")

    enroll = sub.add_parser("enroll", help="Enroll a user's voiceprint")
    enroll.add_argument("--user", required=True)

    sub.add_parser("list-voiceprints", help="List enrolled voiceprints")

    test_file = sub.add_parser("test-file", help="Run pipeline on a wav file")
    test_file.add_argument("--path", type=Path, required=True)

    return parser


async def run_file(settings: Settings, path: Path) -> None:
    bus = EventBus()
    pipeline = RuntimePipeline(settings, bus)
    audio = read_wav_mono_16k(path)
    frame_size = int(settings.sample_rate * settings.frame_ms / 1000)
    mono = now_monotonic()
    for i in range(0, len(audio), frame_size):
        frame = audio[i : i + frame_size]
        if len(frame) < frame_size:
            frame = np.pad(frame, (0, frame_size - len(frame)))
        await pipeline.handle_frame(AudioFrame(samples=frame.astype(np.float32), monotonic_ts=mono + (i / settings.sample_rate)))


def do_enroll(settings: Settings, user: str) -> None:
    embedder = SpeakerEmbedder(settings.speaker_model)
    service = EnrollmentService(embedder, settings.speaker_model, auth_threshold=settings.auth_threshold)
    store = VoiceprintStore(settings.data_dir / "voiceprints")

    print(f"Enrolling user '{user}'. Read each sentence, then paste path to a 16k wav capture.")
    segments = []
    for idx, sentence in enumerate(ENROLLMENT_SENTENCES, start=1):
        print(f"[{idx}/{len(ENROLLMENT_SENTENCES)}] {sentence}")
        wav_path = Path(input("wav path> ").strip())
        segments.append(read_wav_mono_16k(wav_path))

    result = service.build_voiceprint(user=user, segments=segments, sample_rate=settings.sample_rate)
    path = store.save(result.voiceprint)
    print(f"Saved voiceprint: {path}")


def list_voiceprints(settings: Settings) -> None:
    store = VoiceprintStore(settings.data_dir / "voiceprints")
    items = store.load_all()
    if not items:
        print("No voiceprints found")
        return
    for vp in items:
        print(f"- {vp.user}: samples={vp.sample_count}, dims={vp.embedding.shape[0]}, created={vp.created_at}")


def main() -> None:
    configure_logging()
    parser = build_parser()
    args = parser.parse_args()
    settings = Settings.from_file(args.config)
    ensure_data_dirs(settings)

    if args.cmd == "run":
        asyncio.run(RuntimePipeline(settings, EventBus()).run_microphone())
    elif args.cmd == "serve":
        app = build_app(settings, EventBus())
        uvicorn.run(app, host="0.0.0.0", port=8000)
    elif args.cmd == "enroll":
        do_enroll(settings, args.user)
    elif args.cmd == "list-voiceprints":
        list_voiceprints(settings)
    elif args.cmd == "test-file":
        asyncio.run(run_file(settings, args.path))
        LOGGER.info("test_file_completed path=%s", args.path)


if __name__ == "__main__":
    main()
