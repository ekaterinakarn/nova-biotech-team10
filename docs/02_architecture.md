# 02 — Architecture

## The pipeline in one line

```
Source (12ch) → filter 8–30 Hz → 2s windows → covariance → fidelity score
   → smooth → Frame (JSON) → WebSocket 20 Hz → browser → hand at 60 fps
```

Each arrow throws away detail that doesn't carry information:

```
 RAW            FILTERED       WINDOWS         COVARIANCE      FIDELITY
 12 × 38400  →  8–30 Hz     →  n × 12 × 321 →  n × 12 × 12  →  one number, 0–1
```

## The three seams (`src/contracts.py`) — nobody edits this file alone

The whole system is decoupled at three interfaces so that four people can build in parallel and we
can swap components (especially sim→file→live) by changing one line.

### 1. `Source` — where samples come from

Interchangeable implementations, same interface:

- `SimSource` — synthetic ERD; how you unit-test a BCI with no hardware.
- `FileSource` — replays a real PhysioNet recording at true speed. **The Mac demo.**
- `LiveSource` — BrainFlow → ANT Neuro eego. Written blind now, run on Windows on Sept 12.

Contract (shapes matter): a source yields windows of shape `(n_channels, n_times)` and can provide
calibration windows labelled exec vs rest.

### 2. `FidelityScorer` — the original contribution

```python
scorer.calibrate(X_exec, X_rest)   # X_*: (n_epochs, n_channels, n_times)
value = scorer.score(X)            # X: (n_channels, n_times) -> float in [0, 1]
```

Per-person, direction-agnostic, few-trials. See `docs/04_fidelity-design.md`.

### 3. `Frame` — what goes over the wire

A small dataclass serialized to JSON, emitted 20× per second. The browser interpolates toward the
latest frame at 60 fps — **never drive the mesh directly from the socket** or it judders at 20 Hz.

| Field | Type | Drives | Meaning |
|---|---|---|---|
| `t` | float | — | timestamp (seconds) |
| `fidelity` | float 0–1 | the **meter/bar** | raw truth, unsmoothed |
| `activation` | float 0–1 | the **hand** | smoothed fidelity (EMA), for a fluid hand |
| `state` | str | UI label | `"engaged"` / `"ambiguous"` / `"rest"` |
| `condition` | str | demo screen | which demo condition is active (squeeze/imagine/…) |
| `signal_ok` | bool | grey-out | electrode/signal quality gate |
| `coaching` | str | prompt text | the closed-loop instruction to the user |
| `d_exec` | float | debug/overlay | distance to the movement template |
| `d_rest` | float | debug/overlay | distance to the rest template |

`fidelity` vs `activation` is deliberate: the bar shows the honest raw number (so the dip during
visual imagery is visible), the hand shows the smoothed number (so it renders fluidly on screen).

## The "one-line swap" story (why the build order is safe)

We are never more than one step from something demonstrable:

1. 3D hand driven by a **slider**, no EEG at all.
2. Slider replaced by **`SimSource`** (synthetic data).
3. Sim replaced by **`FileSource`** — a real recording, replayed at true speed. ← the Mac demo.
4. File replaced by **`LiveSource`** — the live amplifier. One line, on Sept 12.

If the hardware or its drivers fail on build day, we fall back one step and still have a full demo
driven by real brain data.

## Module map

```
src/
  contracts.py   the three seams above (frozen)
  config.py      every constant (deck quotes these verbatim)
  data.py        PhysioNet → (n, 12, n_times) arrays; the offline data path
  fidelity.py    covariance + Riemannian distance + calibrate/score
  sources.py     SimSource / FileSource / LiveSource
  server.py      the realtime loop: window → score → smooth → Frame → WebSocket
scripts/
  00_setup_check.py   verify the environment
  01_explore.py       first figures (ERD, PSD, CSP topomap)
  02_validate.py      the go/no-go: does fidelity separate imagery from rest?
  03_replay_demo.py   run FileSource → server end-to-end without the browser (smoke test)
ui/
  index.html app.js hand.js styles.css   the browser hand
```
