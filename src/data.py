"""Load PhysioNet EEG data and turn it into the (n_epochs, n_channels, n_times) arrays
that the rest of the pipeline consumes.

This is the offline data path (see docs/03_datasets.md). It handles the two classic
silent bugs in EEGMMIDB code:
    1. Channel names come with trailing dots / odd case ('Fc3.', 'C3..'). We call
       mne.datasets.eegbci.standardize() BEFORE picking channels or setting a montage.
    2. T1/T2 mean different things in different runs. We only ever load runs of one
       type at a time and document which is which via config's run lists.

Array-shape vocabulary (see contracts.py):
    raw        : mne Raw, 12 channels, filtered 8-30 Hz + 60 Hz notch
    epochs     : mne Epochs, one per annotated event (T0 rest / T1 / T2)
    X          : (n_epochs, n_channels, n_times) float array from epochs.get_data()
"""

from __future__ import annotations

import numpy as np
import mne
from mne.datasets import eegbci
from mne.io import concatenate_raws, read_raw_edf

from src import config

# EEGMMIDB is verbose to load; keep the console readable. Scripts can override this.
mne.set_log_level("WARNING")


def load_raw(subject: int, runs: list[int], *, filtered: bool = True) -> mne.io.BaseRaw:
    """Download (if needed) and assemble PhysioNet runs into one filtered 12-channel Raw.

    Args:
        subject:  PhysioNet subject number, 1..109.
        runs:     which runs to concatenate (all must be the SAME task type; see
                  config.REAL_LR_RUNS / IMAGINE_LR_RUNS so T1/T2 stay consistent).
        filtered: apply the 60 Hz notch + 8-30 Hz band-pass (True for real use;
                  False only if a script wants the unfiltered signal).

    Returns:
        mne Raw restricted to config.CHANNELS (our 12 leads), optionally filtered.
    """
    # eegbci.load_data downloads the EDF files on first call and caches them in
    # mne's data dir; on later calls it just returns the local paths.
    paths = eegbci.load_data(subject, runs, update_path=True)
    raw = concatenate_raws([read_raw_edf(p, preload=True) for p in paths])

    # Fix 'Fc3.'/'C3..' -> 'FC3'/'C3' so pick() and the montage line up (docs/03).
    eegbci.standardize(raw)
    raw.set_montage("standard_1005")

    # Keep only our deliberate 12-lead montage (requirement R1).
    raw.pick(config.CHANNELS)

    if filtered:
        # 60 Hz mains hum (North America — NOT 50). Then 8-30 Hz: mu (8-12) + beta
        # (13-30), where motor imagery lives, which also drops blinks (<4 Hz) and jaw
        # EMG (>30 Hz) for free.
        raw.notch_filter(config.NOTCH_HZ)
        raw.filter(config.BAND_HZ[0], config.BAND_HZ[1])

    return raw


def load_epochs(
    subject: int,
    runs: list[int],
    *,
    tmin: float = 0.0,
    tmax: float = config.WINDOW_SEC,
    filtered: bool = True,
) -> mne.Epochs:
    """Cut the annotated events (T0/T1/T2) of the given runs into fixed-length epochs.

    Args:
        subject:   PhysioNet subject number.
        runs:      runs of ONE task type (see load_raw).
        tmin,tmax: epoch window relative to each event onset, in seconds. Default
                   0..2 s gives our scoring window; 01_explore uses e.g. -1..4 s to
                   show the ERD dip around the cue.

    Returns:
        mne Epochs; epochs.event_id maps 'T0'/'T1'/'T2' to integer codes.
        epochs.get_data() is (n_epochs, 12, n_times); n_times = round((tmax-tmin)*fs)+1
        (e.g. 2 s at 160 Hz -> 321 samples).
    """
    raw = load_raw(subject, runs, filtered=filtered)
    # PhysioNet stores the task markers as annotations ('T0','T1','T2'); turn them
    # into an MNE events array + label->code mapping.
    events, event_id = mne.events_from_annotations(raw)
    return mne.Epochs(
        raw,
        events,
        event_id=event_id,
        tmin=tmin,
        tmax=tmax,
        baseline=None,      # no baseline correction: we compare covariance, not amplitude
        preload=True,
        picks="eeg",
    )


def _windows_for_labels(epochs: mne.Epochs, labels: list[str]) -> np.ndarray:
    """Return (n, 12, n_times) data for the requested annotation labels, or an empty
    array shaped (0, 12, n_times) if none of them are present in these epochs."""
    present = [lab for lab in labels if lab in epochs.event_id]
    if not present:
        return np.empty((0, len(config.CHANNELS), len(epochs.times)))
    return epochs[present].get_data(copy=True)


def condition_windows(subject: int) -> dict[str, np.ndarray]:
    """Assemble, for one subject, the arrays the fidelity score needs.

    We treat this as an ENGAGEMENT problem (not left-vs-right), so we pool T1 (left
    fist) and T2 (right fist) into a single "movement" / "imagery" class and use T0 as
    rest (see docs/00 and docs/04).

    Returns dict of (n_epochs, 12, n_times) arrays:
        exec         : real fist movement   (runs 3/7/11, T1+T2) -> movement template
        rest         : rest                 (T0 in those runs)   -> rest template
        imagery      : imagined fist        (runs 4/8/12, T1+T2) -> the test condition
        imagery_rest : rest during imagery  (T0 in imagery runs) -> held-out rest test
    """
    move = load_epochs(subject, config.REAL_LR_RUNS)
    imagine = load_epochs(subject, config.IMAGINE_LR_RUNS)
    return {
        "exec": _windows_for_labels(move, ["T1", "T2"]),
        "rest": _windows_for_labels(move, ["T0"]),
        "imagery": _windows_for_labels(imagine, ["T1", "T2"]),
        "imagery_rest": _windows_for_labels(imagine, ["T0"]),
    }


if __name__ == "__main__":
    # Smoke test: load one subject and print what we got. First run downloads ~6 EDF
    # files (a few MB) into mne's cache; later runs are instant.
    mne.set_log_level("ERROR")
    subj = 1
    raw = load_raw(subj, config.REAL_LR_RUNS)
    print(f"subject {subj}: {len(raw.ch_names)} channels @ {raw.info['sfreq']:.0f} Hz")
    print("channels:", raw.ch_names)
    for name, X in condition_windows(subj).items():
        print(f"  {name:<12} {X.shape}")
