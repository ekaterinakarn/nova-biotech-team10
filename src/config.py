"""Every constant in one place.

Why centralise: every parameter (filter band, window length, channels, ...) has exactly one
authoritative value, and changing it changes the whole system at once — no magic numbers
scattered across files. See docs/03_datasets.md and docs/04_fidelity-design.md.
"""

from __future__ import annotations

# --------------------------------------------------------------------------- #
# Channels — our deliberate 12-lead montage (challenge requirement R1).
# --------------------------------------------------------------------------- #
# Motor core + Laplacian ring + three context channels. Names are standard 10-05
# (data.py calls mne.datasets.eegbci.standardize() so PhysioNet's 'C3..'/'Fc3.'
# become these clean names before we pick them).
CHANNELS: list[str] = [
    "FC3", "FC4",                 # premotor, left/right
    "C3", "C1", "Cz", "C2", "C4", # primary motor strip (the ERD core)
    "CP3", "CP4",                 # postcentral, completes the Laplacian ring
    "Fz",                         # frontal-midline theta -> cognitive effort (fatigue branch)
    "Pz",                         # parietal -> engagement/attention (fatigue branch)
    "Oz",                         # occipital -> eyes-open sanity check (fatigue branch)
]

# The occipital-leak fix (see docs/03): the fidelity/classifier input uses ONLY the
# motor channels. Fz/Pz/Oz are kept in CHANNELS for the fatigue/effort branch and the
# eyes-open sanity check, but excluded from the covariance features so the model can't
# cheat by reading occipital alpha through Oz.
CONTEXT_CHANNELS: list[str] = ["Fz", "Pz", "Oz"]
MOTOR_CHANNELS: list[str] = [c for c in CHANNELS if c not in CONTEXT_CHANNELS]

N_CHANNELS: int = len(CHANNELS)          # 12
N_MOTOR: int = len(MOTOR_CHANNELS)       # 9

# Positions of the motor channels within a 12-channel window, so the fidelity scorer can
# slice them out of a full (12, n_times) array: [0,1,2,3,4,5,6,7,8] here.
MOTOR_IDX: list[int] = [CHANNELS.index(c) for c in MOTOR_CHANNELS]

# --------------------------------------------------------------------------- #
# Sampling & windowing.
# --------------------------------------------------------------------------- #
# PhysioNet EEGMMIDB is 160 Hz. The live eego samples faster; sources.py sets its own
# fs and the server derives window length from the source's fs, not from this constant.
# This value is the default for the OFFLINE (data.py / validation) path.
FS: float = 160.0                        # Hz (PhysioNet)

WINDOW_SEC: float = 2.0                  # each scored window is 2 seconds
STEP_SEC: float = 0.5                    # slide the window 0.5 s each tick -> ~4 scores/s offline


def window_samples(fs: float = FS) -> int:
    """Number of time samples in one window at a given sampling rate.

    2 s at 160 Hz -> 320 samples (+1 endpoint in some MNE epoching -> 321). Derived,
    never hard-coded, so the live path (higher fs) just works.
    """
    return int(round(WINDOW_SEC * fs))


WINDOW_SAMPLES: int = window_samples(FS)  # 320 at 160 Hz

# --------------------------------------------------------------------------- #
# Filtering (see docs/08 for the physiology).
# --------------------------------------------------------------------------- #
# 8–30 Hz spans mu (8–12) and beta (13–30) — where motor imagery lives — and is also a
# free artifact filter: eye blinks are <4 Hz and jaw EMG is >30 Hz, so both are gone.
BAND_HZ: tuple[float, float] = (8.0, 30.0)
NOTCH_HZ: float = 60.0                    # North America mains hum (NOT 50 Hz)

# --------------------------------------------------------------------------- #
# Fidelity scorer (see docs/04).
# --------------------------------------------------------------------------- #
SHRINKAGE: float = 0.05                   # covariance regularization toward identity (keeps SPD)
RIEMANN_METRIC: str = "logeuclid"         # "logeuclid" (default) or "riemann" (affine-invariant)

# Exponential-moving-average smoothing: activation = SMOOTHING*prev + (1-SMOOTHING)*fidelity.
# Higher = smoother hand but laggier. Tune on build day if the hand judders/lags.
SMOOTHING: float = 0.7

# State labels from the raw fidelity value (for Frame.state / the UI).
ENGAGED_THRESHOLD: float = 0.60
REST_THRESHOLD: float = 0.40

# --------------------------------------------------------------------------- #
# Realtime server / WebSocket.
# --------------------------------------------------------------------------- #
WS_HOST: str = "127.0.0.1"
WS_PORT: int = 8765
STREAM_HZ: float = 20.0                   # frames per second on the wire (UI interpolates to 60)

# --------------------------------------------------------------------------- #
# PhysioNet run maps (see docs/03 — the #1 silent bug: T1/T2 differ by run).
# --------------------------------------------------------------------------- #
REAL_LR_RUNS: list[int] = [3, 7, 11]      # real movement: T1=left fist,  T2=right fist
IMAGINE_LR_RUNS: list[int] = [4, 8, 12]   # imagined:      T1=left fist,  T2=right fist
REAL_BOTH_RUNS: list[int] = [5, 9, 13]    # real:          T1=both fists, T2=both feet
IMAGINE_BOTH_RUNS: list[int] = [6, 10, 14]# imagined:       T1=both fists, T2=both feet

# Subjects with known-bad recordings — exclude from validation.
EXCLUDED_SUBJECTS: list[int] = [88, 89, 92, 100, 104]
