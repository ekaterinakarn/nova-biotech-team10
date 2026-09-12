"""Bridge: read an amplifier with BrainFlow and re-publish it as an LSL stream.

Why this exists (docs/15): BrainFlow's ANT Neuro (eego) backend only runs on
Windows/Linux, so it cannot stream to a Mac directly. Run this bridge ON THE WINDOWS
laptop that is plugged into the eego 24; it acquires with BrainFlow and pushes an LSL
outlet that any machine on the network (your Mac's `--source lsl`) can consume.

It also lets us test the whole BrainFlow -> LSL -> pipeline path with NO hardware, using
BrainFlow's built-in synthetic board (--board-id -1), which runs on macOS too.

Usage:
    # Real eego 24 on Windows (board id + rows + electrode labels from the pinouts):
    python scripts/06_brainflow_to_lsl.py --board-id <ID> \
        --channel-rows 1,2,3,4,5,6,7,8,9,10,11,12 \
        --labels FC3,FC4,C3,C1,Cz,C2,C4,CP3,CP4,Fz,Pz,Oz

    # No-hardware test (synthetic board), anywhere:
    python scripts/06_brainflow_to_lsl.py --board-id -1 \
        --labels FC3,FC4,C3,C1,Cz,C2,C4,CP3,CP4,Fz,Pz,Oz
"""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from brainflow.board_shim import BoardShim, BrainFlowInputParams
from pylsl import StreamInfo, StreamOutlet


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--board-id", type=int, required=True, help="BrainFlow board id (-1 = synthetic)")
    ap.add_argument("--serial-port", default="")
    ap.add_argument("--channel-rows", help="comma-separated board rows; default = the board's EEG rows")
    ap.add_argument("--labels", required=True, help="electrode labels in the SAME order as --channel-rows")
    ap.add_argument("--name", default="NeuroLoopTest")
    args = ap.parse_args()

    labels = [c.strip() for c in args.labels.split(",")]

    params = BrainFlowInputParams()
    params.serial_port = args.serial_port
    board = BoardShim(args.board_id, params)
    fs = BoardShim.get_sampling_rate(args.board_id)

    # Which board rows to publish. Default to the board's EEG rows, trimmed to len(labels).
    if args.channel_rows:
        rows = [int(r) for r in args.channel_rows.split(",")]
    else:
        rows = BoardShim.get_eeg_channels(args.board_id)[:len(labels)]
    if len(rows) != len(labels):
        ap.error(f"got {len(rows)} rows but {len(labels)} labels; they must match")

    # Advertise the LSL stream with the electrode labels (what LslSource matches on).
    info = StreamInfo(args.name, "EEG", len(rows), fs, "float32", "neuroloop-bridge")
    channels = info.desc().append_child("channels")
    for name in labels:
        channels.append_child("channel").append_child_value("label", name)
    outlet = StreamOutlet(info)

    board.prepare_session()
    board.start_stream()
    print(f"Bridging board {args.board_id} @ {fs:.0f} Hz -> LSL '{args.name}' "
          f"({len(rows)} channels {labels}). Ctrl+C to stop.")
    try:
        while True:
            data = board.get_board_data()          # new samples since last call
            if data.shape[1]:
                chunk = data[rows, :].T            # (n_samples, n_channels)
                outlet.push_chunk(chunk.tolist())
            time.sleep(0.05)
    except KeyboardInterrupt:
        print("\nstopping")
    finally:
        board.stop_stream()
        board.release_session()
    return 0


if __name__ == "__main__":
    sys.exit(main())
