"""A synthetic LSL EEG outlet to rehearse the live path with NO hardware.

Publishes an LSL stream (real channel labels, oscillating-covariance data) so that
`python src/server.py --source lsl` — on this machine or another on the same network —
shows the hand moving. That proves the whole LSL path end to end before build day.
See docs/15_lsl-live-runbook.md.

Usage:
    python scripts/05_lsl_test.py                      # eego 12-lead @ 250 Hz
    python scripts/05_lsl_test.py --montage unicorn    # 8-channel Unicorn layout
    python scripts/05_lsl_test.py --channels C3,Cz,C4 --fs 512
"""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src import config

from pylsl import StreamInfo, StreamOutlet


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--montage", choices=list(config.MONTAGES), default="eego")
    ap.add_argument("--channels", help="comma-separated labels, overrides --montage")
    ap.add_argument("--fs", type=float, default=250.0)
    ap.add_argument("--name", default="NeuroLoopTest")
    args = ap.parse_args()

    labels = ([c.strip() for c in args.channels.split(",")] if args.channels
              else config.MONTAGES[args.montage])
    n = len(labels)

    # Advertise the stream with per-channel labels (this is what LslSource matches on).
    info = StreamInfo(args.name, "EEG", n, args.fs, "float32", "neuroloop-test")
    channels = info.desc().append_child("channels")
    for name in labels:
        channels.append_child("channel").append_child_value("label", name)
    outlet = StreamOutlet(info)
    print(f"Publishing '{args.name}': {n} channels {labels} @ {args.fs:.0f} Hz. Ctrl+C to stop.")

    # Two covariance signatures; slowly oscillate between them so fidelity rises and falls.
    rng = np.random.default_rng(0)
    Ae = rng.standard_normal((n, n)); sig_exec = Ae @ Ae.T + n * np.eye(n)
    Ar = rng.standard_normal((n, n)); sig_rest = Ar @ Ar.T + n * np.eye(n)

    chunk = max(1, int(args.fs * 0.1))     # push ~10 chunks/second
    dt = chunk / args.fs
    phase = 0.0
    try:
        while True:
            phase += 2 * np.pi * dt / 10   # ~10 s oscillation period
            w = 0.5 * (1 + np.sin(phase))
            sigma = (1 - w) * sig_rest + w * sig_exec
            samples = rng.multivariate_normal(np.zeros(n), sigma, size=chunk)
            outlet.push_chunk(samples.tolist())
            time.sleep(dt)
    except KeyboardInterrupt:
        print("\nstopped")
    return 0


if __name__ == "__main__":
    sys.exit(main())
