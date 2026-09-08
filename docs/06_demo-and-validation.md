# 06 — Demo & Validation (how we show it isn't fake)

A hand moving on screen proves nothing on its own — a BCI demo can be secretly driven by jaw
clenches. The demo and the validation are designed to be **falsifiable**.

## The go/no-go validation (decides the headline)

**Question:** does the fidelity score separate genuine imagery from rest, per person, across many
people? Run `scripts/02_validate.py`.

**Method:**
1. For each of ~20 PhysioNet subjects: build `C_exec` from **real** movement runs (3/7/11) and
   `C_rest` from rest (T0) windows — this is `calibrate()`.
2. Score held-out **imagery** windows (runs 4/8/12) and held-out **rest** windows.
3. Test whether fidelity(imagery) > fidelity(rest) with `permutation_test_score` (1000 shuffles).
4. Report **accuracy + Cohen's kappa + per-subject spread**, cross-validated **subject-wise**
   (never shuffled epochs from one subject — adjacent overlapping windows leak and inflate accuracy).

**Decision rule:**
- **Separates (p < 0.05 across subjects)** → headline result: the score measures imagery engagement.
- **Doesn't** → fall back to left/right CSP+LDA classification (already 73.3% on subject 001) and
  say so. Both outcomes are recoverable because this is tested *this week*, not on build day.

Also run the CSP+LDA baseline **with and without Fz/Pz/Oz** to quantify the occipital-leak fix — the
accuracy delta is worth reporting.

## The four falsifiability tools

1. **CSP topomap** (`csp.plot_patterns()`) — if the blobs sit over motor cortex, the model found
   brains; if frontal/occipital, it learned eye movement/alpha. Anatomical evidence, not a
   black-box number.
2. **Permutation test** (1000 shuffles) — the honest way to claim above-chance with small n.
3. **Sham toggle** — break the model on purpose (shuffle the templates) and watch the meter collapse
   to chance. This doubles as the sham-control arm of a future trial.
4. **Artifact challenge** — clenching, blinking, and looking side to side keep the output flat (the
   8–30 Hz band kills blinks <4 Hz and jaw EMG >30 Hz); imagining moves it. This addresses the
   "isn't that just muscle?" objection directly.

## The 5-condition live demo

A fidelity bar next to the arm, live, on a volunteer wearing the cap:

| Instruction | Expected bar | Why |
|---|---|---|
| "Actually squeeze your hand." | **high** | the reference — real execution |
| "Now imagine it — feel the tension." | **high**, arm moves | kinesthetic imagery reproduces the pattern |
| "Now just watch it in your mind, like a video." | **drops** | visual imagery largely doesn't produce ERD |
| "Now count backwards from 300 by sevens." | **flat** | cognitive load, not motor imagery |
| "Back to feeling it." | **climbs** | re-engaging motor cortex |

The point: existing clinical trials of this therapy cannot tell those four conditions apart; this
does it in about ninety seconds with twelve electrodes.

## End-to-end verification checklist

- [ ] `python scripts/00_setup_check.py` → all imports OK (passes on the M4).
- [ ] `pytest tests/` → fidelity ≈1/0/0.5 on synthetic exec/rest/mixed; hand-rolled distance matches
      pyriemann within tolerance; `Frame` round-trips JSON.
- [ ] `python scripts/01_explore.py` → ERD figure shows the C3/C4 dip after cue.
- [ ] `python scripts/02_validate.py` → permutation p-value + kappa printed, figure saved.
- [ ] `python src/server.py --source file` + open `ui/index.html` → hand moves from a real recording.
- [ ] Sept 12: `--source live` on Windows → same server + UI against the eego.
- [ ] **Record a backup video** of the working FileSource demo before presenting.
