# 01 — Requirements (traceability)

The challenge's core requirements, what each means for us, and the file(s) that satisfy it.

| ID | Requirement (handout) | What it means for us | Satisfied by |
|---|---|---|---|
| **R1** | Algorithm that recognizes meaningful signals within a **12-lead** EEG data set (feature extraction) | Work in a ~12-channel montage, not 64. Pick our 12 deliberately and defend the choice. Extract covariance features, not raw voltage. | `src/config.py` (the 12 channels), `src/data.py` (filter+epoch), `src/fidelity.py` (covariance features) |
| **R2** | Correlate these signals to real-time performance to predict cognitive/physical success at a task | The decoded signal must predict a **measurable outcome** — genuine imagery vs rest — not just "we detected alpha." Prove it with a statistical test. | `src/fidelity.py` (the score), `scripts/02_validate.py` (permutation test, kappa) |
| **R3** | Create a form of output to communicate with the user | A UI. The virtual hand + fidelity bar + coaching text. | `ui/`, `src/server.py` (Frame stream) |
| **R4** | **Closed-loop**: the system adapts its output accordingly | The output must change the task, which changes the brain state, which changes the output. If the arrow only goes one way, we've failed the core ask. | `src/server.py` (fidelity → coaching/task adaptation in the Frame), `ui/` (renders the adaptation) |
| **R5** | Real-world implication, target market, projected business strategy | Named customer, named payer, numbers. | `docs/07_deck-outline.md` (business section) |

## How R4 (the closed loop) is actually closed

Most teams will build a one-way arrow: read brain → show result. That is *not* a loop. Ours closes
because the fidelity score **feeds back into what the system asks for**:

- Fidelity slipping toward the "visual imagery" pattern → prompt changes: *"Stop picturing it. Feel
  the tension in your forearm."*
- Fidelity dropping from fatigue → shorter trials, more rest.
- Fidelity high and stable → harder task.

The user's next brain state is a consequence of the system's last output. That is the loop. See
`docs/06_demo-and-validation.md` for the 5-condition demo that makes this visible.

## Deliverables checklist (due Sept 13)

- [ ] One commented code file with **team number + all four names at the top** (`.py` accepted).
      → we will produce a single self-contained `neuroloop_10.py` export in addition to the repo,
      so the deliverable is one file but the repo stays modular. (See build plan.)
- [ ] Pitch deck as **both** `.pptx` and `.pdf`, named `10_buildathon`.
- [ ] Be able to **explain any line on the spot** and present how AI was used (AI policy).
