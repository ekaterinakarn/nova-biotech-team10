"""Headless end-to-end smoke test: FileSource -> scorer -> Frame, printed to the console.

Runs the exact pipeline the server runs, minus the WebSocket/browser, so you can confirm
the loop works (and eyeball the fidelity trace on a real recording) without opening a page.

Usage:
    python scripts/03_replay_demo.py [subject] [n_windows]     # defaults 1, 40
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.fidelity import FidelityScorer
from src.server import _state_and_coaching
from src.sources import FileSource


def main() -> int:
    subject = int(sys.argv[1]) if len(sys.argv) > 1 else 1
    n = int(sys.argv[2]) if len(sys.argv) > 2 else 40

    source = FileSource(subject=subject)
    scorer = FidelityScorer()
    scorer.calibrate(*source.calibration_windows())
    print(f"subject {subject}: calibrated; streaming {n} windows\n")

    stream = source.stream()
    for i in range(n):
        window = next(stream)
        fidelity = scorer.score(window)
        state, coaching = _state_and_coaching(fidelity)
        bar = "#" * int(fidelity * 30)
        print(f"{i:>3} {fidelity:4.2f} |{bar:<30}| {state:<9} {coaching}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
