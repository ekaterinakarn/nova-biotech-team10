# 09 — Handoff: the 3D hand

This document is self-contained: it has everything needed to build a 3D version of the
virtual hand **without touching any Python, EEG, or server code**. The bottom section is a
prompt you can paste directly into another AI tool.

## Context (what the hand is)

NeuroLoop reads a person's motor-cortex engagement from EEG and produces one number per
window — `activation`, in [0, 1] — where 0 means "at rest / not engaging" and 1 means
"fully engaging the motor cortex" (imagining a fist clench). A virtual hand mirrors that
number: **0 = open hand, 1 = closed fist.** When the person genuinely does the exercise,
the hand closes; when they drift, it opens. That visual feedback is the therapy.

## The architecture seam (why this is a clean, isolated task)

The browser has two layers with one seam between them:

- **`ui/app.js` owns the data.** It opens the WebSocket, reads each `Frame`, and runs a
  60 fps loop that eases a value toward the latest `activation`. It calls **one function**
  every frame. You do not touch this file.
- **`ui/hand.js` owns the rendering, and nothing else.** It exports exactly:

  ```js
  createHand(container) -> { applyPose(activation, meta) }
  ```

  - `activation`: number in [0, 1]. **0 = open hand, 1 = closed fist.**
  - `meta`: `{ state: "engaged" | "ambiguous" | "rest", signalOk: boolean }`.

The current `hand.js` implements this with Canvas 2D (procedural fingers that curl). **A 3D
hand is simply a different `hand.js` that implements the same export.** Everything
upstream — EEG → fidelity score → WebSocket → 60 fps interpolation — stays identical.

`app.js` already does all smoothing/interpolation, so `applyPose` should map `activation`
straight to a pose with **no smoothing or timers of its own**.

## Colors for `meta.state` (match the existing UI)

| state | color |
|---|---|
| engaged | `#39d98a` (green) |
| ambiguous | `#f5c451` (amber) |
| rest | `#8a94a6` (grey-blue) |

When `meta.signalOk` is `false`, dim/desaturate the hand (bad electrode signal).

## How to test with NO EEG and NO Python EEG deps

ES modules must be served over HTTP (not opened as a `file://`). Two options:

1. **Standalone (simplest):** from the repo root run `python -m http.server 8000 -d ui`,
   open `http://localhost:8000`, tick **"Manual slider (no EEG)"**, and drag the slider.
   That drives `applyPose` directly — if the hand moves 0→fist as you drag, it's correct.
   No amplifier, no data files, no ML.
2. **Full loop:** `python src/server.py --source sim` then open `http://127.0.0.1:8766`.
   The hand animates on its own from the (simulated) score.

Because the slider and the live WebSocket both feed the *same* `applyPose`, anything that
works with the slider automatically works with real brain data.

## Constraints / gotchas

- **CDN risk:** an earlier three.js-from-CDN attempt gave a black screen on the demo laptop.
  Keep the current Canvas `hand.js` as a guaranteed fallback; treat the 3D hand as an
  enhancement that only ships once it renders reliably on the actual demo machine.
- **Zero build step preferred.** An ES-module + CDN import, or a single pre-bundled JS file,
  is easier to run on a projector than a toolchain.
- **Must not fail to load.** This is presented live; a hard dependency that can't load is
  worse than a simpler hand that always works.

## Acceptance criteria

- [ ] Exports `createHand(container)` returning `{ applyPose(activation, meta) }` — same
      signature as `ui/hand.js`, so it swaps in with zero changes to `app.js`/`index.html`.
- [ ] `activation` 0 → open hand, 1 → full fist, smooth across the range.
- [ ] Tints by `meta.state`; dims when `meta.signalOk === false`.
- [ ] No internal smoothing/networking; pose maps directly from the argument.
- [ ] Renders reliably from a plain `python -m http.server` (no build step), and the manual
      slider drives it.

## For reference: the `Frame` fields `app.js` receives

`t`, `fidelity` (raw, drives the bar), `activation` (smoothed, drives the hand),
`state`, `condition`, `signal_ok`, `coaching`, `d_exec`, `d_rest`.
(Defined in `src/contracts.py`; you only need `activation`, `state`, `signal_ok`.)

---

## Paste-ready prompt for the other AI tool

> I'm building a browser visual for an EEG neurofeedback demo. I need a **drop-in
> replacement for a file `ui/hand.js`** that renders a **3D hand** using **three.js**
> (import from a CDN) with a **rigged glTF hand model**.
>
> It must export exactly this and nothing incompatible:
> `export function createHand(container) { /* ... */ return { applyPose(activation, meta) } }`
> - `activation`: number 0..1 — **0 = fully open hand, 1 = full fist**. Map it to finger
>   bone rotations or a "fist" blendshape/morph weight = activation.
> - `meta`: `{ state: "engaged"|"ambiguous"|"rest", signalOk: boolean }`. Tint the hand
>   green `#39d98a` / amber `#f5c451` / grey `#8a94a6` by `state`; dim it when
>   `signalOk` is false.
>
> Requirements:
> - Create the three.js scene/camera/renderer inside `createHand(container)` and run your
>   own render loop. But **do NOT add smoothing or any networking** — an external file calls
>   `applyPose` ~60×/sec with an already-interpolated value; just map argument → pose.
> - No build step: use an ES-module CDN import (e.g. import maps for `three` and
>   `GLTFLoader`) so it runs from a plain static file server.
> - Keep it robust: if the glTF fails to load, fall back to a simple procedural hand so the
>   canvas is never blank.
> - Provide the full `hand.js` and tell me exactly which CDN URLs / import-map entries to add
>   to `ui/index.html` (currently it loads `hand.js` as `<script type="module">` via
>   `app.js`).
>
> Test plan I'll use: serve the folder with `python -m http.server`, open it, toggle a manual
> slider that calls `applyPose(value, {state:"engaged", signalOk:true})`, and confirm the
> hand goes open→fist smoothly.
