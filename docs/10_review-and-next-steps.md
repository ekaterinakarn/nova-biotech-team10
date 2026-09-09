# Buildathon review and next steps — September 8, 2026

> Latest update: EEG-only confirmed; hardware first available on build day. The hand now uses a locally bundled rigged GLB. See [EEG-to-hand connection and new validation](12_eeg-to-hand.md), which supersedes earlier renderer/validation status below.

This review supersedes historical completion claims in docs/05 and the backlog in docs/09.
Reviewed source, tests, scripts, UI, docs/00–09, recent git history and the supplied Challenge Handout.pdf.
Historical metrics below have not been re-run in this review.

## Implemented in this pass

- Responsive research dashboard, articulated procedural 3D hand with drag-to-rotate.
  Geometry is projected and depth-sorted in Canvas: offline, no CDN, no Blender installation.
  `applyPose(activation, meta)` remains the visual seam. Original renderer: `ui/hand-2d.js`.
- Manual mode visibly separates pose exploration from model feedback; disconnects and
  stale frames clear the score and dim the hand. Recorded cue labels cannot be replaced
  by arbitrary presenter cues. Synthetic, replay and live sources are labeled.
- Sixty-second trace; browser-session CSV export (last 72,000 frames maximum).
  Score integral counts only valid, non-control, non-manual observed intervals. It is an
  exploratory score integral, not validated therapy dose. Refresh resets browser totals.
- File windows held for two seconds instead of advancing at 20 windows/second.
  This remains an interleaved, curated epoch replay, not chronological continuous EEG.
  Default demo subject 4 is selected for illustration, not an estimate of general performance.
- Acquisition runs outside the async event loop. Frame timestamps use elapsed wall time.
- Calibration-relative variance and kurtosis gate; rejected windows do not drive the hand.
  These heuristics do not prove artifact-free EEG or identify all clipping.
- Live path now requires explicit board ID and 12 channel rows, checks short buffers,
  filters calibration and scoring windows alike, and releases board sessions on exit.
  Hardware, units, startup failure handling, electrode identity and freshness still need device testing.

## Priorities and acceptance criteria

| Priority | Work | Done when |
|---|---|---|
| P0 · organizer | Confirm whether fNIRS is mandatory; obtain exact amplifier, OS/driver requirements, electrode layout and sample data | Written answers and a verified BrainFlow row-to-electrode table |
| P0 · hardware | Test on the actual Windows/Linux machine; verify units, timestamps, repeated/stale buffers and raw quality | Continuous acquisition, clean calibration, unplug/reconnect test, recorded backup |
| P0 · scientific validity | Compare movement vs rest on unseen runs; include artifact/visual imagery/math controls | Per-person AUC, balanced accuracy, kappa, uncertainty and quality rejection rate saved to machine-readable files |
| P1 · validation | Replace CSP shuffled-trial CV with held-out-run evaluation; distinguish personalized calibration from cross-subject transfer | Run-separated estimates, parameters frozen before test; new metrics replace historical numbers |
| P1 · feedback | Counterbalanced rest/imagery blocks and success criterion tied to task performance | Cue timestamps and held-out task outcomes exported; acknowledge cue-following is not independently measured performance |
| P1 · model | Check scale sensitivity of fixed eigenvalue floor; compare continuous and windowed filters | Scale-invariance tests on realistic voltage magnitudes and offline/live feature comparison |
| P1 · calibration | Interleave shorter rest/movement blocks, add countdown UI and held-out quality check | Both classes have adequate clean windows; failed calibration leads to retry |
| P1 · pitch | Clear customer, workflow, alternatives and bottom-up revenue assumptions | Deck covers every handout section; assumptions clearly marked, no invented traction |
| P1 · delivery | Runnable commented submission file and deck exports | Team 10 and all four full names in code; `10_buildathon.pptx` and `.pdf`; clean-machine rehearsal |
| P2 · visual | Optional Blender hand, lighting polish, handedness and anatomical improvements | Licensed GLB with tested open-to-fist animation and offline rendering fallback |

## What the current results actually support

The handoff reports average AUC about 0.60 ± 0.11, pooled kappa about 0.14 and a
subject-level sign-flip p about 0.002 across 20 people. Statistical evidence of a group
shift does not imply dependable individual control. Report effect size and spread next
to the p-value; do not market this as high-accuracy intention decoding.

The fidelity evaluation calibrates each individual on real-movement runs and tests that
individual on separate imagined-movement runs. This is personalized held-out-condition
validation aggregated across subjects, not cross-subject predictive CV. The CSP baseline
uses shuffled trials from one subject; its 73.3% / 77.8% figures must be labeled as such.
A pipeline fits CSP inside the fold (good), but run-level temporal dependence remains.

Dropping Fz/Pz/Oz reduces direct context-channel input; it does not establish cortical
localization or eliminate volume-conducted eye/muscle artifacts. Band-pass filtering
attenuates some artifacts, not all. Visual imagery, mental math and artifact outcomes in
docs/06 are hypotheses to test, not demonstrated separations in the existing dataset.

The identical-template toggle demonstrates a constant 0.5 control, not empirical chance
accuracy or a blinded clinical sham. Existing score means need no threshold, but state
labels still depend on heuristic 0.4/0.6 thresholds. The score is not a probability.

Mathematical corrections: convex arithmetic averages of SPD matrices remain SPD;
log-Euclidean averaging is a modeling choice, not the only valid average. Shrinkage to
trace-scaled identity does not rescue an all-zero covariance; reject such input.

Prior clinical, novelty and regulatory claims need a separate sourced review. Do not
repeat “nobody measured adherence,” guaranteed amputee transfer, “Class I,” or lower
regulatory burden as established facts. This review does not validate those claims.

## Suggested September 8–13 sequence

1. September 8–9: confirm organizer/hardware details, review this implementation together,
   test the UI in the presentation browser, agree on target customer and exact claim.
2. September 9–10: run-separated validation, saved result tables, negative controls,
   calibration UX, prepare hardware configuration and backup data.
3. September 11: freeze demo features; rehearse the story and record the offline demo;
   assemble deliverables and AI-use explanation. No new classifier unless evidence requires it.
4. September 12: hardware integration and artifact challenge first; capture what actually
   works, failure rates included. Tune only on calibration data, preserve a final test block.
5. September 13: update slides with measured results, export both formats, rehearse Q&A.

## Pitch and business work

Lead with a transparent research prototype for personalized motor-imagery feedback.
A suitable initial customer hypothesis is a rehabilitation research lab already equipped
with EEG. Validate the workflow, setup time, repeat calibration burden and value of exported
session records before proposing home use. Interview lab users and compare existing BCI tools.

Use a bottom-up scenario table: sites × annual software price, less onboarding/support and
hardware costs. Any prices and conversion rates are assumptions until supported by interviews.
Show a realistic pilot milestone before a scale forecast. Avoid unsupported medical-device
classification claims. The handout explicitly judges the business plan as well as implementation.

## Team questions

- Is fNIRS required or optional, and is the sponsor's dataset available?
- Which teammate and laptop own amplifier integration? Exact device and cap montage?
- Preferred visual direction and left/right hand? Is a stylized research hand sufficient?
- Full names for the submission, pitch duration, and any final organizer scoring rubric?
- Which person can own scientific validation, customer discovery and deck production?

## AI-use record

This pass used AI to review code and documentation, implement dashboard/renderer and
stream-quality changes, and write regression tests and this plan. Team members should be
able to explain perspective projection, finger-joint angles, covariance distances, quality
heuristics, replay timing and why the displayed score is not a clinical outcome.

## Verification completed in this pass

- `python -m pytest -q`: 17 passed (including new quality, filter, pacing and degenerate-input checks).
- JavaScript syntax checks and `git diff --check`: passed.
- Running synthetic server: HTTP 200, valid WebSocket frames, constant-0.5 control and restore command checked.
- Headless Chrome screenshot inspected: dashboard, 3D hand and received synthetic scores render.
- Not verified: physical amplifier, continuous replay realism, clinical outcomes, mobile interaction,
  browser control interactions beyond the socket check, or a fresh 20-subject validation run.
