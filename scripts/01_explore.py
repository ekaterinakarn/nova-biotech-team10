"""First figures: is the motor-imagery signal actually there?

Produces figures/erd_c3c4.png — mu-band (8-12 Hz) power at C3 and C4 over time, as a
percentage change from a pre-cue baseline, for imagined LEFT vs RIGHT fist, averaged
over subjects. A sustained dip after the cue is event-related desynchronisation (ERD):
the motor cortex engaging (see docs/04_fidelity-design.md). This is the sanity check to
run before any modelling — if the dip isn't here, nothing downstream will work.

Usage:
    python scripts/01_explore.py [n_subjects]     # default 5
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import matplotlib

matplotlib.use("Agg")  # no GUI needed; we only save a PNG
import matplotlib.pyplot as plt
import mne

# Allow `python scripts/01_explore.py` to find the `src` package (repo root on path).
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src import config, data

mne.set_log_level("ERROR")

FIG_DIR = Path(__file__).resolve().parents[1] / "figures"
MU_BAND = (8.0, 12.0)      # the mu rhythm; ERD is clearest here (narrower than our 8-30)
TMIN, TMAX = -1.0, 4.0     # window around the cue: 1 s before, 4 s after
ERD_WINDOW = (0.5, 2.0)    # where we expect the sustained dip


def mu_epochs(subject: int) -> mne.Epochs:
    """Load one subject's IMAGINED-fist runs, filtered to the mu band, epoched around
    the cue. Returns Epochs with event_id keys 'T0'/'T1'/'T2'."""
    raw = data.load_raw(subject, config.IMAGINE_LR_RUNS, filtered=False)
    raw.notch_filter(config.NOTCH_HZ)
    raw.filter(*MU_BAND)
    events, event_id = mne.events_from_annotations(raw)
    return mne.Epochs(raw, events, event_id, tmin=TMIN, tmax=TMAX,
                      baseline=None, preload=True, picks="eeg")


def _smooth(x: np.ndarray, win_samples: int) -> np.ndarray:
    """Moving-average smooth (boxcar). Squared band-limited signal oscillates at ~2x the
    band frequency; smoothing over ~0.25 s turns it into a readable power envelope."""
    kernel = np.ones(win_samples) / win_samples
    return np.convolve(x, kernel, mode="same")


def power_pct(epochs: mne.Epochs, label: str, channel: str) -> tuple[np.ndarray, np.ndarray]:
    """Mu power over time for one label/channel, as % change from the pre-cue baseline.

    Power = mean over trials of the squared (band-limited) signal, then smoothed into an
    envelope. Baseline = mean power in the pre-cue interval (times < 0). Returns
    (times, pct_change)."""
    x = epochs[label].get_data(picks=[channel])   # (n_trials, 1, n_times)
    power = (x[:, 0, :] ** 2).mean(axis=0)         # (n_times,) average across trials
    power = _smooth(power, int(0.25 * epochs.info["sfreq"]))
    times = epochs.times
    baseline = power[times < 0].mean()
    return times, 100.0 * (power - baseline) / baseline


def main() -> int:
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 5
    subjects = [s for s in range(1, n + 1) if s not in config.EXCLUDED_SUBJECTS]
    print(f"Computing mu-band ERD over {len(subjects)} subject(s): {subjects}")

    # Accumulate each subject's %-change time course, then average across subjects.
    keys = [("T1", "C3"), ("T1", "C4"), ("T2", "C3"), ("T2", "C4")]
    acc: dict[tuple[str, str], list[np.ndarray]] = {k: [] for k in keys}
    times = np.array([])
    for s in subjects:
        ep = mu_epochs(s)
        for lab, ch in keys:
            times, pct = power_pct(ep, lab, ch)
            acc[(lab, ch)].append(pct)

    mean = {k: np.mean(v, axis=0) for k, v in acc.items()}

    # Two panels: imagining LEFT (T1) and imagining RIGHT (T2). In each, C3 (left
    # hemisphere) vs C4 (right). Contralateral control would show the opposite
    # hemisphere dipping more; at the group level it's subtle (see docs/00).
    fig, axes = plt.subplots(1, 2, figsize=(11, 4), sharey=True)
    panels = [(axes[0], "T1", "Imagining the LEFT fist"),
              (axes[1], "T2", "Imagining the RIGHT fist")]
    for ax, lab, title in panels:
        for ch, color in [("C3", "tab:red"), ("C4", "tab:blue")]:
            ax.plot(times, mean[(lab, ch)], color=color, label=ch)
        ax.axvline(0, color="k", lw=0.8, ls="--")          # cue onset
        ax.axhline(0, color="grey", lw=0.6)                # baseline
        ax.axvspan(*ERD_WINDOW, color="grey", alpha=0.12)  # expected ERD window
        ax.set_title(title)
        ax.set_xlabel("seconds from cue")
        ax.legend(loc="upper right", fontsize=8)
    axes[0].set_ylabel("mu-band power (% change from baseline)")
    fig.suptitle(f"Motor imagery ERD — {len(subjects)} subjects, PhysioNet EEGBCI")
    fig.tight_layout()

    FIG_DIR.mkdir(exist_ok=True)
    out = FIG_DIR / "erd_c3c4.png"
    fig.savefig(out, dpi=130)
    print(f"saved {out}")

    # One-line quantitative summary: mean %-change in the ERD window (should be negative).
    in_win = (times >= ERD_WINDOW[0]) & (times <= ERD_WINDOW[1])
    for k in keys:
        print(f"  {k[0]} {k[1]}: mean mu change in {ERD_WINDOW}s = "
              f"{mean[k][in_win].mean():+.1f}%")
    return 0


if __name__ == "__main__":
    sys.exit(main())
