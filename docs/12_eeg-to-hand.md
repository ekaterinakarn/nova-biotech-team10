# EEG to hand: implementation and build-day connection

Confirmed by Emma: 12-channel EEG only; no fNIRS. Physical hardware is unavailable until
September 12. Preparation uses recorded EEG and synthetic windows, not an assumed live test.

## The connection already implemented

```text
12-channel cap + amplifier
    ↓ BrainFlow on the acquisition laptop (driver and board to confirm on build day)
LiveSource → channel order → 2-second 8–30 Hz windows → quality check
    ↓
FidelityScorer: 9 motor channels → covariance → distance to personal movement/rest templates
    ↓
fidelity = distance_to_rest / (distance_to_movement + distance_to_rest)
    ↓ server.py: smooth activation, send JSON over WebSocket at ~20 Hz
app.js: receive activation, interpolate using elapsed time, call applyPose()
    ↓
hand.js: rotate finger bones → skin deforms → Three.js renders the GLB
```

A frame contains `fidelity`, `activation`, `signal_ok`, `state` and distances. The browser
uses raw fidelity for its meter and smoothed activation for the hand. It never consumes raw
EEG voltages directly. A grip of 0 is open, 1 is closed, and intermediate values interpolate
joint rotations. At present this is continuous feedback, not a classifier for arbitrary
hand gestures or individual finger positions. Motor imagination may not produce a full
0-to-1 score range; we do not silently magnify it into apparently perfect control.

The UI shows the current grip percentage. Manual mode bypasses EEG for pose testing and
is explicitly labeled. Invalid/stale input relaxes and dims the hand. The user can drag to
rotate the viewpoint; that changes the camera, not the inferred activation.

## Why the reference helps

[Hand-Detection-3D](https://github.com/imadeddinedjekoune/Hand-Detection-3D) connects
camera-based OpenCV/MediaPipe tracking to Unity through UDP and uses a rigged Blender hand.
We use the same separation of input and rigged animation. Our input is EEG-derived activation,
our transport is WebSocket, and the renderer remains in the browser. No camera, Unity install
or tracking landmarks are required. No source/model from that repo was copied.

Our mesh is the MIT-licensed generic right hand from WebXR Input Profiles, exported from Blender.
It is a continuous skinned mesh rather than intersecting ellipsoids. Its flat-shaded metallic
surface preserves the original stylized feedback colors: gold for ambiguous, jade for engaged,
and slate for rest; it intentionally does not use a skin-colored material. Its initially independent
WebXR joints are reparented into finger chains while preserving bind transforms. Bending those
bones moves the mesh using its skin weights. Thumb opposition has a separate axis and timing.
This is a visual rig, not a biomechanical simulation; inspect and tune the pose in Blender if needed.

Three.js 0.180.0, GLTFLoader, geometry utility and licenses are bundled under `ui/vendor/three`;
`ui/models/right.glb` is local too. No CDN requests occur during rendering. A GLB/WebGL error
replaces the canvas and starts `hand-procedural.js` automatically. The UI identifies fallback mode.

## Before build day

```sh
# No EEG download or hardware required; exercises scoring, socket and rig together.
.venv/bin/python src/server.py --source sim
# Open http://127.0.0.1:8766; leave Manual exploration unchecked.

# Real held-out EEG epochs, calibrated from separate execution recordings.
.venv/bin/python src/server.py --source file --subject 4

# Quality/math/pacing/run-separation regression tests.
.venv/bin/python -m pytest -q

# Reproduce scientific results; writes figures/validation_results.json.
.venv/bin/python scripts/02_validate.py 20
```

Run one server at a time. The first PhysioNet run may download data. Subject 4 is a curated
illustration, not representative of all people. Manual 0/50/100 checks test rendering only.

## September 12 checklist

1. Confirm board ID, supported laptop/driver, sampling rate, voltage units and the 12 electrode
   identities. A 12-signal cap does not establish the channel names/order assumed by our model.
2. Configure `--board-id ID --channel-rows ROWS` with the verified values, in `config.CHANNELS`
   order. These are BrainFlow data rows, not electrode numbers; never guess them.
3. Start `--source live` with those arguments and any necessary serial port. Current calibration
   prompts appear in the terminal: movement/attempt, then rest. Do not call this hardware-tested
   until acquisition, quality and calibration pass on the actual device.
4. Check freshness/timestamps, units, electrode artifacts and held-out imagery/rest blocks.
   Live uses windowed IIR filters; offline results use MNE continuous FIR filtering. Their
   calibration/scoring paths are internally consistent, but offline performance is not a live guarantee.
5. Run blink/jaw/motion controls and log observed rejection/failure rates. Record a backup demo.
6. If the montage differs, update channel selection deliberately and rerun calibration; if the
   sponsor provides LSL rather than BrainFlow, implement that acquisition adapter at the Source boundary.
   The model-to-animation connection does not need to change.

## Validation update from this pass

Twenty subjects: mean AUC 0.602, subject bootstrap 95% interval [0.556, 0.653], pooled accuracy
0.572, kappa 0.143, sign-flip p=0.002. This is an encouraging group effect with limited individual
reliability. It does not validate clinical benefit or arbitrary hand movement decoding.

CSP now holds out one complete imagery run at a time (three folds, subject 1). All 12 channels:
0.800 accuracy; nine motor channels: 0.711. The previous shuffled-trial 0.733/0.778 comparison is
superseded. Removing context electrodes cannot be claimed to improve accuracy here. This CSP
left/right experiment is separate from the engagement score that drives the hand.

The eigenvalue floor is now relative to the matrix spectrum, preserving the score's distance
geometry under common voltage-unit scaling. This does not remove the need to check hardware units.


## Checks completed

- 21 Python tests pass, including voltage-scale invariance and run-isolated CSP evaluation.
- 20-subject validation re-run and saved in `figures/validation_results.json`.
- Browser: open / half grip / closed poses inspected; synthetic-model activation observed
  driving the rendered grip; blocking the GLB request activates the labeled Canvas fallback.
- Physical EEG acquisition, anatomical/clinical validity, and projector performance still require
  build-day checks. The browser checks do not imply hardware has been tested.

### Finger-direction regression

The asset's palmar side is negative X in bind coordinates. Finger flexion therefore rotates
about negative Z; the thumb opposes about positive Y. `ui/hand-rig.js` contains these camera-independent
kinematics. Run `node tests/test_hand_rig.mjs` to check the actual asset's fingertips move
palmward at 10%, 50% and 100% grip, the thumb crosses the palm, and opening restores the bind pose.
The corrected animation was also inspected from the back, side and palm in the browser.


Latest grip correction: native WebXR sibling joints are now posed directly in the shared
armature coordinates, replacing the earlier reparented rig. Finger gathering happens before
flexion in a consistent plane, with intermediate/distal joints folding earlier in closure.
The pose tests also check unchanged bone lengths and limited sideways fingertip drift.
