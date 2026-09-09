# 05 — Build Plan (file-by-file order + timeline)

> September 8 review: see [current implementation, evidence caveats and priorities](10_review-and-next-steps.md). Historical claims and task statuses below are not all verified.

The rule: **build in this order, test each file before the next.** The system is never more than
one step from something demonstrable, and every file is small enough to explain line-by-line.

## Build order

| # | File | Status | Done when |
|---|---|---|---|
| 0 | git repair, `requirements.txt`, `.gitignore`, `README`, `scripts/00_setup_check.py`, venv | ✅ done | setup check passes on the M4 (it does) |
| 1 | `docs/` specs | ✅ done | this folder is filled in |
| 2 | `src/contracts.py` | ✅ done | the three seams importable, `Frame.to_json()` round-trips |
| 3 | `src/config.py` | ✅ done | all constants centralised; `WINDOW_SAMPLES` derived from `FS` |
| 4 | `src/data.py` | ☐ | `load_subject(1)` returns `(n, 12, 321)` with correct labels |
| 5 | `scripts/01_explore.py` | ☐ | ERD-at-C3/C4 figure saved to `figures/` |
| 6 | `src/fidelity.py` | ☐ | `pytest` cross-check vs pyriemann passes; score behaves (1/0/0.5) |
| 7 | `scripts/02_validate.py` | ☐ | permutation p-value + kappa printed; **the go/no-go answer** |
| 8 | `src/sources.py` | ☐ | Sim & File sources yield windows through the contract |
| 9 | `src/server.py` | ☐ | `03_replay_demo.py` streams Frames from a real recording |
| 10 | `ui/` (Canvas hand, bar, demo screen, sham) | ☐ | slider→hand works; then WebSocket→hand |
| 11 | `src/sources.py::LiveSource` on Windows | ☐ | eego streams into the same server (tested pre-Sept 12 if possible) |
| 12 | deck `10_buildathon.pptx` + `.pdf` | ☐ | all required sections covered; exported both formats |
| 13 | single-file deliverable `neuroloop_10.py` + names header | ☐ | one runnable file with team number + names at top |

## Timeline (today = Sept 7; hardware = Sept 12; due = Sept 13)

- **Sun Sept 7 (today):** Phase 0 done, docs written, `contracts.py` + `config.py` done.
- **Mon–Tue Sept 8–9:** `data.py` + `01_explore.py` (see the signal), then `fidelity.py` + tests.
- **Tue–Wed Sept 9–10:** `02_validate.py` — **run the go/no-go across ~20 subjects.** This decides
  the headline. Start the slider→hand UI.
- **Wed–Thu Sept 10–11:** `sources.py` + `server.py` + `03_replay_demo.py`; wire WebSocket→hand;
  write `LiveSource` blind; draft the EEGgo slide. Full Mac demo working end-to-end.
- **Thu Sept 11:** freeze; deck first draft; rehearse the 5-condition demo on FileSource.
- **Fri Sept 12 (build day):** swap `--source file` → `--source live` on the Windows laptop,
  calibrate on a volunteer, tune. Record a backup video of the working demo immediately.
- **Sat Sept 13:** finalize deck, export both formats, present.

## "Explain every line" discipline

- Each source file opens with a docstring: **what it does, why, and the array shapes**.
- Implement one file per working session and read it back before it's committed.
- The genuinely novel logic (`fidelity.py`) is the shortest file and the best understood.
- Commit messages describe *why*, not just *what*, so the git history is itself a record.

## Git / GitHub

- Fresh `git init` on `main` (done). Commit per file with a clear message.
- Push to a GitHub remote only once every line is understood.
- When ready: create a repo, `git remote add origin …`, push `main`.
