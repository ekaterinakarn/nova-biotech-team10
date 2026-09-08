# 09 — Handoff & Continuation (review · harden · extend)

This is a self-contained brief for continuing the project with another collaborator (human
or AI). The goal is threefold: **(1) re-review every file and the models for correctness,
(2) harden the system so it can't fail on demo day, (3) extend it** (the 3D hand, stretch
goals). It lists the honest known gaps so nothing is discovered on Sept 12.

Read `docs/00`–`08` for the *why*; this doc is the *what to do next*.

---

## 1. How to run everything (and what "correct" looks like)

From the repo root, with the venv active (`source .venv/bin/activate`):

| Command | What it proves | Expected |
|---|---|---|
| `python scripts/00_setup_check.py` | environment imports | all ✅ on Python 3.13 / arm64 |
| `pytest tests/ -q` | fidelity math + Frame | **10 passed** |
| `python scripts/01_explore.py 10` | the signal is real | `figures/erd_c3c4.png`, ERD dips −9…−17% |
| `python scripts/02_validate.py 20` | the headline claim | **p≈0.002**, AUC 0.60±0.11, κ≈0.14; CSP 73.3% (12ch) / 77.8% (motor-only) |
| `python scripts/03_replay_demo.py 4 40` | end-to-end, headless | fidelity trace swings on subject 4 |
| `python src/server.py --source file --subject 4` + open `http://127.0.0.1:8766` | full live loop | hand moves from a real recording |

Reference shapes: `data.condition_windows(1)` → four `(45, 12, 321)` arrays, 12 channels @ 160 Hz.

---

## 2. Repository map — what each file does and what to scrutinize

| File | Role | Re-review focus |
|---|---|---|
| `src/contracts.py` | the 3 seams (Source, FidelityScorer, Frame) | signatures stable? Frame fields sufficient? |
| `src/config.py` | all constants | channel list, band, window, thresholds sane? `MOTOR_IDX` correct? |
| `src/data.py` | PhysioNet load/filter/epoch | **run-map T1/T2 correct**; `standardize()` before pick; no baseline leakage |
| `src/fidelity.py` | **the model** (covariance + Riemannian distance) | SPD safety, shrinkage, clip; matches pyriemann (tests) |
| `src/sources.py` | Sim/File/Live | **LiveSource is unverified** (see §3); FileSource demo subject |
| `src/server.py` | realtime loop, WebSocket, coaching | **filtering gap** (see §3); `signal_ok` hardcoded |
| `scripts/0X_*.py` | setup / explore / validate / replay | subject-wise CV, no epoch leakage |
| `ui/*` | Canvas hand + controls | `applyPose` contract; interpolation in `app.js` only |
| `tests/*` | fidelity + contracts | extend coverage (see §5) |

---

## 3. Known gaps & foolproofing backlog (prioritized, honest)

### P0 — correctness / demo-critical
- **`LiveSource` is written blind and untested.** The board id (`ANT_NEURO_EE_410_BOARD`),
  the channel→row mapping (`eeg_rows[:12]`), units, and scaling are all guesses. Confirm each
  with the ANT Neuro mentor on Windows *before* Sept 12, and verify the 12 rows actually map
  to FC3…Oz in the right order. This is the single biggest risk.
- **The realtime path does not band-pass/notch live windows.** `FileSource` windows are
  pre-filtered (via `data.load_raw`) and `SimSource` is synthetic, but `LiveSource` yields
  *raw* board data. So on live hardware the covariance is computed on unfiltered signal —
  blinks/EMG/drift will corrupt it, and calibration vs scoring won't match the offline
  science. **Fix:** apply the 8–30 Hz band-pass + 60 Hz notch in the realtime loop (or inside
  `LiveSource`) so every window the scorer sees is filtered like the offline path. Filtering
  each 2 s window with `scipy.signal` (or a stateful streaming filter) is enough.
- **`LiveSource.stream()` shape guard.** `get_current_board_data(n)` can return fewer than
  `n_times` samples right after start; guard for short buffers before computing covariance.
  Also the `stream()` sleep expression is a confusing no-op (`WINDOW_SEC*STEP_SEC/WINDOW_SEC`
  == `STEP_SEC`); simplify it.
- **Demo subject.** Default `--subject 1` is weak (AUC 0.58, fidelity flat ~0.5). Use a
  strong subject for the file demo (e.g. **4** → AUC 0.93, or 7/15). Consider making the
  server default to a known-good subject.

### P1 — robustness
- **`Frame.signal_ok` is hardcoded `True`.** Implement a real signal-quality gate: detect
  flat channels, saturation/clipping, and abnormally high per-channel variance, and set
  `signal_ok=False` so the hand honestly greys out instead of showing a confident-wrong
  number. This also strengthens the artifact-challenge demo.
- **Artifact handling beyond the band-pass.** The 8–30 Hz filter drops blinks (<4 Hz) and jaw
  EMG (>30 Hz), but large in-band motion artifacts still leak. Add variance/kurtosis-based
  window rejection for the "clench/blink/look" challenge to stay flat reliably.
- **Calibration quality.** Live calibration uses fixed time blocks and trusts the user's
  timing. Consider more/longer windows, sliding (overlapping) windows for more data, and a
  quality check that rejects a bad calibration before it becomes the template.
- **Server startup race.** `server.py` needs ~3–4 s (the `mne` import) before the WebSocket
  is up; the browser auto-reconnects so it's fine, but a readiness log/signal would be tidier.

### P2 — extensions
- **3D hand** (see §6).
- **Session dose.** Integrate fidelity over a session (∑ fidelity·Δt) → the "measured dose"
  no trial in this field reports. Small addition, big pitch payoff.
- **Left/right stretch goal.** The CSP+LDA path already hits 73.3%; expose it as an optional
  2-class mode.
- **Sliding-window streaming** for smoother live scoring (score every 0.25–0.5 s over a
  2 s window) rather than discrete epochs.

---

## 4. The models — how to independently verify them

- **Fidelity score (`src/fidelity.py`)** — the original contribution. Verify: covariance is
  SPD (symmetric, positive eigenvalues); `riemannian_distance` matches `pyriemann` for both
  `logeuclid` and `riemann` (tests already do this to 1e-6); `score` → ~1 on movement-like,
  ~0 on rest-like, ~0.5 ambiguous; the score is a *ratio* so no magic threshold. Math is
  written out in `docs/04`.
- **Validation (`scripts/02_validate.py`)** — the go/no-go. Verify the split has no leakage
  (templates from *real* runs 3/7/11, test on *imagined* runs 4/8/12), CV is **subject-wise**,
  and the permutation test is a paired sign-flip across subjects. Re-run with more subjects to
  tighten the estimate. Current result: separates with p≈0.002 (n=20).
- **CSP baseline** — reproduces the 73.3% figure on subject 1 and shows the occipital-leak fix
  (dropping Fz/Pz/Oz → 77.8%). Sanity-check the CSP topomap sits over motor cortex (`docs/06`).

---

## 5. Suggested re-review checklist

- [ ] Array shapes consistent everywhere: `(n_epochs, 12, n_times)`, covariance `(9|12, 9|12)`.
- [ ] Run-map T1/T2 usage matches `docs/03` (the #1 silent bug).
- [ ] No data leakage: calibration vs test windows are disjoint; CV is subject-wise.
- [ ] SPD/regularization safe for degenerate inputs (flat channel, tiny variance).
- [ ] Filtering is applied consistently on *all* sources that reach the scorer (see §3).
- [ ] Fidelity handles degenerate distances (both zero) without NaN.
- [ ] Tests extended: a `data.py` shape test, a `sources.py` contract test, a `server` frame test.
- [ ] Every file still explainable line-by-line (AI policy).

---

## 6. The 3D hand (one extension task, fully isolated)

The visuals are decoupled: `ui/app.js` owns the WebSocket + 60 fps interpolation and calls
**one function**; `ui/hand.js` only renders a pose. A 3D hand is just a different `hand.js`
with the same export — nothing upstream changes.

```js
createHand(container) -> { applyPose(activation, meta) }
//   activation : 0..1   (0 = open hand, 1 = closed fist)
//   meta       : { state: "engaged"|"ambiguous"|"rest", signalOk: boolean }
```

Colors: engaged `#39d98a`, ambiguous `#f5c451`, rest `#8a94a6`; dim when `signalOk` is false.

**Test with no EEG/Python-ML:** `python -m http.server 8000 -d ui`, open it, tick "Manual
slider", drag → the hand should go open→fist. Slider and live WebSocket feed the same
`applyPose`, so slider-correct ⇒ live-correct.

**Constraints:** an earlier three.js-from-CDN attempt gave a black screen on the demo laptop —
keep the current Canvas hand as a guaranteed fallback, prefer no build step (ES-module CDN
import / import maps), and fall back to a procedural hand if the glTF fails to load.

### Paste-ready prompt for the other AI tool

> Build a **drop-in replacement for `ui/hand.js`** that renders a **3D hand** with
> **three.js** (CDN import) and a **rigged glTF hand model**. Export exactly
> `export function createHand(container) { ... return { applyPose(activation, meta) } }`.
> `activation` is 0..1 — **0 = open hand, 1 = full fist** — map it to finger-bone rotations
> or a "fist" blendshape weight. `meta` is `{ state, signalOk }`: tint green `#39d98a` /
> amber `#f5c451` / grey `#8a94a6` by `state`, dim when `signalOk` is false. Create the
> scene/camera/renderer and your own render loop inside `createHand`, but **do NOT add
> smoothing or networking** — an external file calls `applyPose` ~60×/sec with an
> already-interpolated value. No build step (use ES-module CDN imports / import maps). If the
> glTF fails to load, fall back to a simple procedural hand so the canvas is never blank.
> Give me the full `hand.js` and the exact import-map/CDN lines to add to `ui/index.html`
> (it currently loads `app.js` as `<script type="module">`, which imports `hand.js`).
> I'll test by serving `ui/` with `python -m http.server` and dragging a manual slider that
> calls `applyPose(value, {state:"engaged", signalOk:true})`.
