# NeuroLoop — Team 10

**A closed-loop EEG system for phantom limb pain therapy.**
NOVATech × McHacks Buildathon 2026, sponsored by ANT Neuro.

> We measure whether a user is *genuinely engaging their motor cortex* — scored against their
> own attempted-movement signature — and drive a virtual hand on screen in proportion to that
> score. It turns an invisible, unverifiable therapy into a measurable dose.
> **EEG is the instrument, not the drug.**

---

## What this repo contains

| Path | What it is |
|---|---|
| `src/` | The pipeline: contracts, config, data loading, the fidelity score, sources, realtime server |
| `scripts/` | Runnable entry points: setup check, exploration figures, the validation go/no-go, replay demo |
| `ui/` | The browser hand (Canvas 2D, zero dependencies) |
| `docs/` | Specs & design docs — the *why* behind every decision (start at `docs/00_overview.md`) |
| `tests/` | Unit tests (fidelity behaviour, hand-rolled-vs-pyriemann cross-check, Frame JSON) |
| `figures/` | Generated plots (validation, ERD, CSP topomaps) |
| `CLAUDE.md` | The master project spec + build-order table |

## Quick start (macOS / Windows / Linux)

```bash
python3 -m venv .venv
source .venv/bin/activate            # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python scripts/00_setup_check.py     # confirms every import works on your machine
```

## Run the demo with no hardware (the Mac path)

```bash
python src/server.py --source file   # replays a real PhysioNet recording at true speed
# then open ui/index.html in a browser — the hand moves from real brain data
```

On **Sept 12** we swap `--source file` for `--source live` (BrainFlow → ANT Neuro eego,
Windows/Linux laptop). Nothing else changes — that is the point of the `Source` seam.

## The architecture in one line

```
Source (12ch) → filter 8–30 Hz → 2s windows → covariance → fidelity score
   → smooth → Frame (JSON) → WebSocket 20 Hz → browser → hand at 60 fps
```

See `docs/02_architecture.md` for the three seams and the Frame schema.

## Data & science, briefly

- **Dataset:** PhysioNet EEG Motor Movement/Imagery (109 subjects, 64ch, 160 Hz). See `docs/03_datasets.md`.
- **The original contribution** is the *fidelity score* (`src/fidelity.py`): a per-person,
  direction-agnostic Riemannian distance measuring how much a 2-second window looks like *your own*
  movement vs *your own* rest. See `docs/04_fidelity-design.md`.

## Documentation conventions

Every source file carries docstrings stating *what, why, and array shapes*;
every design choice is written down in `docs/`.