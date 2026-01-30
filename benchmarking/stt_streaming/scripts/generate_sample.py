#!/usr/bin/env python
from __future__ import annotations

import argparse
from pathlib import Path

from sttstream.util.sample_data import generate_sine_wav, write_text


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--wav", type=Path, required=True)
    parser.add_argument("--text", type=Path, required=True)
    parser.add_argument("--duration", type=float, default=1.0)
    parser.add_argument("--sample-rate", type=int, default=16000)
    parser.add_argument("--freq", type=float, default=440.0)
    parser.add_argument("--phrase", type=str, default="hello world")
    args = parser.parse_args()

    generate_sine_wav(args.wav, duration_s=args.duration, sample_rate=args.sample_rate, freq_hz=args.freq)
    write_text(args.text, args.phrase)


if __name__ == "__main__":
    main()
