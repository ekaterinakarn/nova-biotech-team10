"""The go/no-go: does the fidelity score actually separate imagery from rest?

This is the project's central claim (docs/06). For each subject we build the movement and
rest templates from the REAL-movement runs, then score held-out IMAGINED windows and rest
windows and ask whether imagery scores higher. We report:

    - per-subject and pooled accuracy of fidelity > 0.5 separating imagery vs rest
    - mean ROC-AUC across subjects (threshold-free)
    - Cohen's kappa (chance-corrected)
    - a paired sign-flip PERMUTATION TEST across subjects -> p-value

Then a second, independent baseline: CSP+LDA left-vs-right imagery classification on one
subject, WITH vs WITHOUT Fz/Pz/Oz, to quantify the occipital-leak fix (docs/03).

Usage:
    python scripts/02_validate.py [n_subjects]      # default 20
"""

from __future__ import annotations

import sys
import json
from pathlib import Path

import numpy as np
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import mne
from mne.decoding import CSP
from sklearn.discriminant_analysis import LinearDiscriminantAnalysis
from sklearn.metrics import accuracy_score, cohen_kappa_score, roc_auc_score
from sklearn.model_selection import LeaveOneGroupOut, cross_val_score
from sklearn.pipeline import Pipeline

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src import config, data
from src.fidelity import FidelityScorer

mne.set_log_level("ERROR")
FIG_DIR = Path(__file__).resolve().parents[1] / "figures"


# --------------------------------------------------------------------------- #
# Part A: the fidelity go/no-go.
# --------------------------------------------------------------------------- #
def fidelity_go_no_go(subjects: list[int]):
    """For each subject: calibrate on real movement vs rest, then test on imagined vs
    rest windows. Returns per-subject mean-fidelity differences, pooled (true, pred)
    labels for kappa/accuracy, and per-subject AUCs."""
    diffs, aucs = [], []
    records = []
    all_true, all_pred = [], []
    for s in subjects:
        cw = data.condition_windows(s)
        if min(len(cw["exec"]), len(cw["rest"]), len(cw["imagery"]),
               len(cw["imagery_rest"])) == 0:
            print(f"  subject {s}: missing a condition, skipping")
            continue

        scorer = FidelityScorer()                 # motor channels only, by default
        scorer.calibrate(cw["exec"], cw["rest"])

        f_imag = np.array([scorer.score(w) for w in cw["imagery"]])
        f_rest = np.array([scorer.score(w) for w in cw["imagery_rest"]])

        diffs.append(f_imag.mean() - f_rest.mean())
        scores = np.concatenate([f_imag, f_rest])
        labels = np.concatenate([np.ones(len(f_imag)), np.zeros(len(f_rest))])
        aucs.append(roc_auc_score(labels, scores))
        records.append(dict(subject=s, auc=float(aucs[-1]),
                            imagery_mean=float(f_imag.mean()), rest_mean=float(f_rest.mean()),
                            accuracy=float(accuracy_score(labels, scores > .5)),
                            kappa=float(cohen_kappa_score(labels, scores > .5)),
                            n_imagery=len(f_imag), n_rest=len(f_rest)))
        all_true.extend(labels.tolist())
        all_pred.extend((scores > 0.5).astype(int).tolist())
        print(f"  subject {s:>3}: AUC {aucs[-1]:.2f}  "
              f"fidelity imagery {f_imag.mean():.2f} vs rest {f_rest.mean():.2f}")

    return np.array(diffs), np.array(all_true), np.array(all_pred), np.array(aucs), records


def sign_flip_test(diffs: np.ndarray, n_perm: int = 1000, seed: int = 0):
    """Paired permutation test. Under the null (imagery and rest exchangeable), the sign
    of each subject's fidelity difference is random. Shuffle signs n_perm times and see
    how often the permuted mean is as extreme as the observed one."""
    rng = np.random.default_rng(seed)
    observed = diffs.mean()
    mags = np.abs(diffs)
    count = 0
    for _ in range(n_perm):
        signs = rng.choice([-1.0, 1.0], size=len(diffs))
        if abs((signs * mags).mean()) >= abs(observed):
            count += 1
    p = (count + 1) / (n_perm + 1)                # +1: never report p == 0
    return observed, p


# --------------------------------------------------------------------------- #
# Part B: CSP+LDA left/right baseline, with vs without Fz/Pz/Oz.
# --------------------------------------------------------------------------- #
def csp_lda_accuracy(subject: int, motor_only: bool) -> tuple[float, float]:
    """Leave-one-run-out CSP/LDA; no trial from a test run enters training."""
    windows, labels, groups = [], [], []
    for run in config.IMAGINE_LR_RUNS:
        epochs = data.load_epochs(subject, [run])[["T1", "T2"]]
        windows.append(epochs.get_data(copy=True))
        labels.extend((epochs.events[:, -1] == epochs.event_id["T2"]).astype(int))
        groups.extend([run] * len(epochs))
    X, y = np.concatenate(windows), np.array(labels)
    if motor_only:
        X = X[:, config.MOTOR_IDX, :]             # keep the 9 motor channels

    clf = Pipeline([
        ("csp", CSP(n_components=6, reg="ledoit_wolf")),
        ("lda", LinearDiscriminantAnalysis()),
    ])
    cv = LeaveOneGroupOut()
    scores = cross_val_score(clf, X, y, cv=cv, groups=np.array(groups), error_score="raise")
    return scores.mean(), scores.std()


# --------------------------------------------------------------------------- #
def main() -> int:
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 20
    subjects = [s for s in range(1, n + 1) if s not in config.EXCLUDED_SUBJECTS]

    print(f"\n=== Part A: fidelity go/no-go over {len(subjects)} subjects ===")
    diffs, y_true, y_pred, aucs, records = fidelity_go_no_go(subjects)
    if not len(diffs):
        raise ValueError("No valid subjects")

    acc = accuracy_score(y_true, y_pred)
    kappa = cohen_kappa_score(y_true, y_pred)
    observed, p = sign_flip_test(diffs)

    print("\n  --- results ---")
    print(f"  subjects tested            : {len(diffs)}")
    print(f"  mean ROC-AUC (imagery/rest): {aucs.mean():.3f} ± {aucs.std():.3f}")
    print(f"  pooled accuracy (>0.5)     : {acc:.3f}")
    print(f"  Cohen's kappa              : {kappa:.3f}")
    print(f"  mean fidelity diff (imag-rest): {observed:+.3f}")
    print(f"  permutation p-value        : {p:.4f}")
    verdict = "group-level shift detected; inspect effect size and individual spread" if p < 0.05 else "no clear group-level shift"
    print(f"  VERDICT: {verdict}")

    print(f"\n=== Part B: CSP+LDA left/right baseline (subject 1) ===")
    acc12, std12 = csp_lda_accuracy(1, motor_only=False)
    acc9, std9 = csp_lda_accuracy(1, motor_only=True)
    print(f"  all 12 channels (incl. Oz): {acc12:.3f} ± {std12:.3f}")
    print(f"  9 motor channels only     : {acc9:.3f} ± {std9:.3f}")
    print(f"  occipital-leak delta      : {acc12 - acc9:+.3f}")

    rng = np.random.default_rng(0)
    bootstrap = np.mean(rng.choice(aucs, size=(5000, len(aucs)), replace=True), axis=1)
    interval = np.quantile(bootstrap, [.025, .975]).tolist()
    report = dict(subjects=records, mean_auc=float(aucs.mean()),
                  mean_auc_subject_bootstrap_95ci=interval,
                  accuracy=float(acc), kappa=float(kappa), permutation_p=float(p),
                  fidelity_protocol="personal execution calibration, separate imagery runs",
                  csp_protocol="leave-one-imagery-run-out, subject 1",
                  csp_12ch=dict(mean=float(acc12), sd=float(std12)),
                  csp_motor=dict(mean=float(acc9), sd=float(std9)))
    FIG_DIR.mkdir(exist_ok=True)
    (FIG_DIR / "validation_results.json").write_text(json.dumps(report, indent=2))
    print(f"  mean AUC subject-bootstrap 95% CI: {interval}")

    # Figure: per-subject fidelity difference (imagery - rest), for the deck.
    FIG_DIR.mkdir(exist_ok=True)
    fig, ax = plt.subplots(figsize=(8, 4))
    order = np.argsort(diffs)
    ax.bar(range(len(diffs)), diffs[order],
           color=["tab:green" if d > 0 else "tab:red" for d in diffs[order]])
    ax.axhline(0, color="k", lw=0.8)
    ax.axhline(observed, color="tab:blue", ls="--", lw=1,
               label=f"group mean {observed:+.3f} (p={p:.3f})")
    ax.set_xlabel("subject (sorted)")
    ax.set_ylabel("mean fidelity: imagery − rest")
    ax.set_title("Held-out imagery versus rest: per-subject fidelity difference")
    ax.legend()
    fig.tight_layout()
    out = FIG_DIR / "fidelity_validation.png"
    fig.savefig(out, dpi=130)
    print(f"\nsaved {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
