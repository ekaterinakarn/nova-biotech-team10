"""Record an LSL EEG stream to disk with a timed rest/move/imagine protocol.

Saves a self-labeled recording (each sample tagged with the phase the person was in),
so it can be analyzed offline exactly like the eego .cnt (build a movement template from
the squeeze phase, a rest template, then test the imagine phase).

Usage (with a direct link if discovery is blocked):
    LSLAPICFG=/tmp/lsl_api.cfg python scripts/08_record_lsl.py \
        --name UnicornRecorderRawDataLSLStream --out unicorn_session
"""

from __future__ import annotations

import argparse
import csv
import sys
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from pylsl import StreamInlet, resolve_streams


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--name", default=None, help="LSL stream name substring (else first EEG)")
    ap.add_argument("--out", default="lsl_session", help="output basename (saved to ~/Downloads)")
    ap.add_argument("--phases", default="rest:20,squeeze:30,rest:15,imagine:20",
                    help="comma list of phase:seconds")
    args = ap.parse_args()
    phases = [(p.split(":")[0], float(p.split(":")[1])) for p in args.phases.split(",")]

    streams = resolve_streams(wait_time=10.0)
    cand = [x for x in streams if (args.name in x.name()) if args.name] or \
           [x for x in streams if x.type() == "EEG"]
    if not cand:
        print("No EEG LSL stream found.")
        return 1
    inlet = StreamInlet(cand[0], max_buflen=120)
    info = inlet.info()
    fs, nch = info.nominal_srate(), info.channel_count()
    print(f"recording '{info.name()}' @ {fs:.0f} Hz, {nch} channels")

    samples, times, labels = [], [], []
    for name, dur in phases:
        print(f">>> PHASE: {name.upper()} for {dur:.0f}s", flush=True)
        end = time.monotonic() + dur
        while time.monotonic() < end:
            chunk, ts = inlet.pull_chunk(timeout=1.0, max_samples=int(fs))
            if chunk:
                samples.extend(chunk); times.extend(ts); labels.extend([name] * len(chunk))
    print(">>> DONE", flush=True)

    arr, t, lab = np.asarray(samples), np.asarray(times), np.asarray(labels)
    out = Path.home() / "Downloads" / args.out
    np.savez(str(out) + ".npz", data=arr, times=t, labels=lab, fs=fs, name=info.name())
    with open(str(out) + ".csv", "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["time", "phase"] + [f"ch{i}" for i in range(nch)])
        for i in range(len(arr)):
            w.writerow([t[i], lab[i]] + list(arr[i]))
    print(f"saved {out}.npz and {out}.csv  ({arr.shape[0]} samples, "
          f"{arr.shape[0]/fs:.0f}s)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
