# Demo explained and dataset priorities

Updated September 8, 2026. This guide supersedes the historical demo claims in document 06.

## Purpose

rEEGain is a research prototype for personalized motor-imagery feedback. We ask whether EEG recorded while someone imagines a movement resembles their own movement calibration more than their rest calibration. A virtual hand makes that score visible. Rehabilitation is a possible future application; pain reduction, therapeutic benefit, and performance in amputees have not been demonstrated.

The hand does not decode individual finger positions. One smoothed scalar drives a predefined open-to-grip animation. The score is pattern similarity, not a probability of imagining correctly, a pain measurement, or a validated measure of imagery vividness.

## Participant workflow

1. A technician fits the cap and checks electrode contact. Confirm amplifier model, acquisition software, channel labels, reference, sample rate and signal units.
2. Acquire EEG through the manufacturer's supported system. A proposed portable route is acquisition computer → LSL → model computer; our LSL receiver is not implemented yet. Direct BrainFlow acquisition exists but is untested on the event equipment.
3. Calibrate on that participant and session: the current live code collects 60 seconds of movement and 60 seconds of rest. Setup and calibration happen before the short stage presentation. Movement calibration can include muscle artifacts, so it is not pure brain ground truth.
4. During testing, keep the physical hand relaxed and imagine the sensation of squeezing, alternating with rest. Keep eyes and posture comparable across conditions.
5. The model filters the signal, checks basic quality, and compares covariance patterns from two-second windows with personal movement/rest templates. Live processing advances every 0.5 seconds.
6. A higher movement-similarity score makes the virtual hand close further; a lower score makes it open further. Smoothing produces fluid animation, not independent new EEG estimates every animation frame. Response takes seconds.
7. Log scores, quality and independent task labels. Cue labels must not drive the hand in model-feedback mode. Manual and synthetic modes cannot count as EEG evidence.

## Proposed presentation (after fitting and calibration)

- Explain the question and identify whether the source is live EEG or recorded EEG.
- Demonstrate three short rest/imagery pairs, about 10 seconds per condition, while showing the hand and score trace.
- Show a summary of separately collected held-out blocks and the multi-participant offline results.
- Explain signal-quality handling and show a clearly labelled recorded backup if acquisition fails.

This is a presentation proposal, not a claim that an automated trial runner exists. A longer, counterbalanced test before the pitch is needed for credible metrics; six short stage blocks alone are not a robust validation study. Watching the feedback can itself change EEG, so include matched or no-feedback validation blocks when testing specificity.

## What counts as success

Engineering: verified real EEG reaches the model; scores reach the browser without cue-driven animation; stream interruptions and rejected windows are visible; latency and rejection rate are recorded.

Model: held-out imagery tends to score above held-out rest across repeated trials and participants. Report ROC AUC, balanced accuracy using a threshold selected only on calibration/training data, rest false activations, participant spread, and rejected-window counts. Split by trials/runs, not randomly across overlapping windows.

Scientific: report artifact sensitivity rather than assuming it away. Bandpass filtering and the current variance/kurtosis checks do not guarantee removal of eye or muscle activity. Motor-channel selection and scalp maps do not establish a unique cortical source. A significant group effect does not establish reliable control for each person.

Current saved report (`figures/validation_results.json`): 20 participants; mean AUC 0.602, participant-bootstrap 95% interval 0.556–0.653; pooled accuracy 57.2%. Subject 4 has AUC 0.934 and is a selected strong replay example, not the average. Calibration uses execution data and testing uses separate imagery runs; this is personalized evaluation, not a model trained on other participants and transferred to an unseen person. The separate left/right CSP benchmark answers a different question.

The constant-score control displays 0.5. It is not a validated clinical sham or a statistical chance-performance test. Integrated score-seconds are exploratory feedback metrics, not therapeutic dose.

## Dataset priorities

1. **PhysioNet EEGMMIDB:** already integrated; 109 participants, real and imagined movements, 64 electrodes, 160 Hz. Freeze the method before evaluating additional participants; preserve separate calibration/test runs and report everyone evaluated. https://physionet.org/content/eegmmidb/1.0.0/
2. **Organizer ANT share:** initial ZIP headers show `EEG_flipcup/`, `Behavioral Data/` and `Video/`. Recordings and task labels have not been inspected; do not assume motor imagery is present. The archive is about 2.6 GB and the bounded file-index request was unsuccessful. Request/download EEG and protocol separately from video. Determine event codes, timing, channel names, units, reference, sample rate, and behavioral outcomes. Actual flip-cup movement could support a task-performance analysis, but motion artifacts and missing imagery labels prevent treating it as interchangeable imagery training data. User-provided link: https://www.dropbox.com/scl/fo/1lc3fl8ur3g4npkajije0/AFnJXWPD8LU4H_TEHLO4HHQ?rlkey=ytwlbq501xecdswxwpwii4y0a&st=0zqdp3rz&e=1&dl=0
3. **Cho et al. (2017):** a promising external dataset with 52 participants, imagery, real movement and additional non-task recordings including jaw activity. Verify access to the original task subsets and their labels before building an adapter; an imagery-only loader may omit useful controls. https://doi.org/10.1093/gigascience/gix034
4. **Stieger et al. (2021):** 62 participants in repeated online sensorimotor-rhythm BCI sessions. Useful later for questions about feedback and learning; its control task differs from our execution-calibrated hand demo. https://www.nature.com/articles/s41597-021-00883-1

Do not concatenate datasets blindly: harmonize channel identities, references, sample rates, units, filtering and task definitions, and keep an independent test set. More EEG is useful only when its labels answer our question.
