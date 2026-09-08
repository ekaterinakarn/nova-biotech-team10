# NeuroLoop — Team 10

Closed-loop EEG system for phantom limb pain therapy.
**NOVATech × McHacks Buildathon 2026, sponsored by ANT Neuro.**

Team: Emma (software eng), Katie (comp eng),
Yasmine (comp eng), Ann (bio/physiology).

---

## Dates

| | |
|---|---|
| **Sept 12** | Build day. First and only access to the EEG hardware |
| **Sept 13** | Deliverables due, pitch + judging |

Deliverables: one commented `.py` with team number and all four names at the top, plus
the deck as **both** `.pptx` and `.pdf` named `10_buildathon`.

**AI policy:** allowed, but we must be able to explain any line on the spot and present
how we used it. Build file by file to be able to defend every line.

---

## What we're building

> A 12-channel closed-loop system that measures whether the user is **genuinely engaging
> their motor cortex**, scored against their own attempted-movement signature, driving a
> virtual hand on screen. It turns an invisible, unverifiable therapy into a measurable dose.

### The problem, in one paragraph

~60% of amputees get phantom limb pain. Motor-imagery therapies help, but the evidence is
a mess — a 2023 review of *placebo-controlled* mirror therapy trials found no efficacy, and
a 2024 RCT (n=80) found decoded execution was no better than plain imagery. **The hole in
every one of those studies: nobody measured whether the patient was actually doing the
exercise.** Motor imagery is invisible. That's a measurement problem, and it's ours.

Framing: **EEG is the instrument, not the drug.** We are not claiming to cure pain. We are
building the dosimeter the field lacks.

---

## Decisions already made — do not relitigate

**Engagement, not left-vs-right classification.** A phantom limb patient has *one* missing
arm; they don't need to choose between hands. Binary detection is also easier and more
accurate than 3-class discrimination. Left/right is a stretch goal only.

**Browser + Canvas 2D for the hand, not Unity, not WebGL.** We tried three.js from a CDN and
got a black screen. The current renderer has zero external dependencies and cannot fail to
load on a projector. `applyPose(a)` is the single entry point — swapping in a rigged glTF
model rewrites one function.

**Riemannian distance, not band-power thresholds.** See "the science" below.

**12 channels:** FC3 FC4 · C3 C1 Cz C2 C4 · CP3 CP4 · Fz Pz Oz.
Motor core + Laplacian ring + Fz (frontal-midline theta, effort) + Pz (engagement) +
Oz (eyes-open sanity check).

---

## The science that drives the code

**ERD (event-related desynchronisation).** When a piece of cortex starts working, its
rhythm gets *weaker*. Motor imagery suppresses mu (8–12 Hz) over sensorimotor cortex.
Contralateral: left-hand imagery → right hemisphere (C4).

**Why we do NOT threshold ERD magnitude.** Kimura et al. (n=20) found subjective imagery
vividness was **not** correlated with ERD magnitude. What *did* correlate was the
**similarity** between the sensorimotor pattern during real movement and during imagined
movement (r = −0.69 and −0.73). Good imagers don't produce a bigger signal — **they
reproduce their own movement signature.** This is the entire basis of the fidelity score.

**Amputees may show inverted ERD.** A 2022 study found mu power *increase* during imagery
where controls show a decrease. A magnitude threshold would break; a pattern-similarity
measure survives. This is why the method must be direction-agnostic and per-person.

**Do NOT build pain detection.** OpenNeuro ds006921 (13 amputees with PLP, 6 without,
19 controls, pre-registered) found **no** pain-specific oscillatory markers. Claiming to
detect phantom pain from EEG would be indefensible in Q&A.

---

## Known issue to fix

`figures/csp_patterns.png` — the strongest learned CSP filter is a blob at the **back** of
the head. The model is partly reading occipital alpha through Oz, not motor cortex. Fix:
exclude Fz/Pz/Oz from the classifier input, keep them for the fatigue branch. Report the
accuracy difference — it's a slide.

---

## Data

**PhysioNet EEG Motor Movement/Imagery** — 109 subjects, 64ch, 160 Hz, EDF+.
`mne.datasets.eegbci.load_data()`, one line, free.

Run map — **T1/T2 mean different things in different runs, this is the #1 silent bug:**

| Runs | Task | T1 | T2 |
|---|---|---|---|
| 3, 7, 11 | **Real** movement | left fist | right fist |
| 4, 8, 12 | **Imagined** | left fist | right fist |
| 5, 9, 13 | Real | both fists | both feet |
| 6, 10, 14 | Imagined | both fists | both feet |

T0 = rest in every run. Commonly excluded subjects: 88, 89, 92, 100, 104.

**The pairing that matters:** runs 3/7/11 and 4/8/12 are the *same people* doing the real
thing and then imagining it. Execution template + imagery test condition, already recorded.
That's what makes the fidelity score validatable before we ever touch hardware.

Verified baseline: CSP+LDA on our 12 channels, subject 001 → **73.3% (±11.3)**, chance 50%.

---

## Architecture

```
Source (12ch) → filter 8–30 Hz → 2s windows → covariance → fidelity score
   → smooth → Frame (JSON) → WebSocket 20 Hz → browser → hand at 60 fps
```

Three seams, defined in `src/contracts.py`. **Nobody changes that file alone.**

1. **Source** — `SimSource` / `FileSource` / `LiveSource`, interchangeable. On Sept 12 we
   swap one line. Write `SimSource` first: it's how you unit-test a BCI.
2. **FidelityScorer** — `calibrate(X_exec, X_rest)` then `score(X) → (0,1)`.
3. **Frame** — 9 fields over the wire. `fidelity` drives the meter (raw truth),
   `activation` drives the hand (smoothed). Browser interpolates at 60 fps toward the last
   frame — never drive the mesh directly from the socket or it juddens at 20 fps.

---

## Conventions

- Every constant lives in `src/config.py`. The deck quotes exact values from it.
- Docstrings say **what, why, and the array shapes**. Shape confusion
  (`n_epochs, n_channels, n_times`) is the #1 time sink in EEG code.
- Cross-validate **subject-wise**, never on shuffled epochs from one subject — adjacent
  overlapping windows leak between train and test and inflate accuracy.
- Report **Cohen's kappa** alongside accuracy (chance-corrected), plus per-subject spread.
  Name the 15–30% "BCI illiteracy" figure before a judge asks.
- 60 Hz notch, not 50 — North America. European repos get this wrong for us.

---

## Build order

Status legend: ✅ done · 🔄 in progress · ☐ not started. Detailed plan: `docs/05_build-plan.md`.

| # | File | Status |
|---|---|---|
| 0 | git repair, `requirements.txt`, `.gitignore`, `README`, `scripts/00_setup_check.py`, venv | ✅ (setup check passes on M4) |
| 0.5 | `docs/` specs (00–09) | ✅ |
| 1 | `src/contracts.py` — the three seams | ✅ |
| 2 | `src/config.py` — constants | ✅ |
| 3 | `src/data.py` — PhysioNet loading, filtering, epoching | ✅ (subject 1 → (45, 12, 321)) |
| 4 | `scripts/01_explore.py` — first figures | ✅ (`figures/erd_c3c4.png`) |
| 5 | `src/fidelity.py` — **the original contribution** | ✅ (10 tests, pyriemann-verified) |
| 6 | `scripts/02_validate.py` — the go/no-go | ✅ (**GO: p=0.002 over 20 subj**; CSP 73.3%) |
| 7 | `src/sources.py` — sim / file / live | ✅ (live written blind, needs Windows) |
| 8 | `src/server.py` — realtime loop | ✅ (WebSocket loop verified end-to-end) |
| 9 | `ui/` — Canvas 2D hand | ✅ (review/harden/3D handoff: `docs/09_handoff.md`) |

**Environment note:** the full scientific stack (mne 1.12, numpy 2.5, scipy 1.18, scikit-learn 1.9,
pyriemann 0.12, brainflow, websockets) installs and imports cleanly on Python 3.13 / macOS arm64.
The whole offline pipeline + FileSource demo runs on the M4; only `LiveSource` needs Windows/Linux.

---

## Two dates that decide everything

**Can any of our laptops run the amplifier?** BrainFlow's ANT Neuro backend is
**Windows/Linux only**. If we're all on Macs there is no live demo. Yasmine owns this.

**Does the fidelity score separate imagery from rest?** Run the PhysioNet
execution-template vs imagery experiment across ~20 subjects with a permutation test.
Yes → headline result. No → fall back to left/right classification and say so honestly.

Both recoverable if we know early. Both fatal if discovered on Sept 12.

---

## How we prove it isn't fake

A hand moving on screen proves nothing — every judge has seen a BCI demo secretly driven by
jaw clenches. Design the demo to be **falsifiable**:

1. **CSP topomap** — `csp.plot_patterns()`. If the blobs sit over motor cortex, the model
   found brains. If they're frontal, it learned eye movement. Anatomical evidence, not a
   black-box number.
2. **Permutation test** — `permutation_test_score`, 1000 shuffles. The honest way to claim
   above-chance with small n.
3. **Sham toggle** — break the model on purpose on stage, show the meter collapse to chance.
   Also: this is the sham-control arm of the clinical trial we'd propose next.
4. **Artifact challenge** — ask the volunteer to clench, blink, look side to side. Output
   stays flat. Then imagine. It moves. Kills "isn't that just muscle?" before it's asked.

**What we cannot claim:** that it reduces pain, or that it works on amputees at all — no
open motor-imagery data from amputees exists. Say this out loud, then show the trial we'd
run. More trustworthy than claiming a cure.
