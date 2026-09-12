"""Analyze a recorded ANT eego .cnt session with our fidelity score.

Builds a movement template from the '1001/Hand squeezing' markers and a rest template
from a baseline stretch, then scores the '1002/Imagining it' and '1003/Virtual Hand'
segments and plots the fidelity across the whole session with the markers overlaid.

Usage:
    python scripts/07_analyze_cnt.py "/path/to/session.cnt"
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import mne

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.fidelity import FidelityScorer

FIG_DIR = Path(__file__).resolve().parents[1] / "figures"
MOTOR = ["C3", "Cz"]          # C4 was railing in this recording; C3+Cz is a clean motor pair
REST_WINDOW = (130.0, 158.0)  # baseline before the first task marker (assumed sitting still)
WIN_SEC = 2.0


def main() -> int:
    path = sys.argv[1] if len(sys.argv) > 1 else \
        "/Users/emmagailleur/Downloads/Team 8_Yasmine_2026-09-12_12-33-30.cnt"
    raw = mne.io.read_raw_ant(path, preload=True, verbose="ERROR")
    fs = raw.info["sfreq"]
    raw.pick(MOTOR)
    raw.notch_filter(60.0, verbose="ERROR")
    raw.filter(8.0, 30.0, verbose="ERROR")
    data = raw.get_data()                       # (n_motor, n_times), already filtered
    n = int(WIN_SEC * fs)

    ann = raw.annotations
    def onsets(label): return [o for o, d in zip(ann.onset, ann.description) if d == label]

    def windows(onset_list):
        out = []
        for o in onset_list:
            i0 = int(o * fs)
            if i0 + n <= data.shape[1]:
                out.append(data[:, i0:i0 + n])
        return np.stack(out) if out else np.empty((0, len(MOTOR), n))

    exec_on = onsets("1001/Hand squeezing")
    imag_on = onsets("1002/Imagining it")
    vhand_on = onsets("1003/Virtual Hand")
    rest_on = list(np.arange(REST_WINDOW[0], REST_WINDOW[1], WIN_SEC))

    X_exec, X_rest = windows(exec_on), windows(rest_on)
    X_imag, X_vhand = windows(imag_on), windows(vhand_on)

    scorer = FidelityScorer(channel_idx=list(range(len(MOTOR))))
    scorer.calibrate(X_exec, X_rest)
    sc = lambda X: np.array([scorer.score(w) for w in X])

    print(f"channels used (motor): {MOTOR}   fs={fs:.0f} Hz")
    print(f"  hand squeezing (template): {np.round(sc(X_exec), 2)}")
    print(f"  rest baseline  (template): mean {sc(X_rest).mean():.2f}")
    print(f"  IMAGINING IT             : {np.round(sc(X_imag), 2)}")
    print(f"  virtual hand             : {np.round(sc(X_vhand), 2)}")
    if len(X_imag):
        print(f"  --> imagery mean {sc(X_imag).mean():.2f} vs rest mean {sc(X_rest).mean():.2f}")

    # Fidelity across the whole session (sliding 2 s / 0.5 s).
    step = int(0.5 * fs)
    t_axis, fid = [], []
    for i in range(0, data.shape[1] - n, step):
        fid.append(scorer.score(data[:, i:i + n]))
        t_axis.append(i / fs)

    fig, ax = plt.subplots(figsize=(13, 4))
    ax.plot(t_axis, fid, lw=1.0, color="black")
    ax.axhline(0.5, color="grey", lw=0.6)
    ax.axvspan(*REST_WINDOW, color="grey", alpha=0.15, label="rest baseline")
    for o in exec_on:
        ax.axvline(o, color="tab:green", alpha=0.6)
    for o in imag_on:
        ax.axvline(o, color="tab:blue", alpha=0.7)
    for o in vhand_on:
        ax.axvline(o, color="tab:purple", alpha=0.5)
    ax.plot([], [], color="tab:green", label="hand squeezing")
    ax.plot([], [], color="tab:blue", label="imagining")
    ax.plot([], [], color="tab:purple", label="virtual hand")
    ax.set_xlabel("time in session (s)"); ax.set_ylabel("fidelity (0-1)")
    ax.set_title("Fidelity across the recorded eego session (Yasmine)")
    ax.legend(loc="upper left", fontsize=8); ax.set_ylim(0, 1)
    fig.tight_layout()
    FIG_DIR.mkdir(exist_ok=True)
    out = FIG_DIR / "session_fidelity.png"
    fig.savefig(out, dpi=130)
    print(f"saved {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
