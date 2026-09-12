# rEEGain — Team 10

**A closed-loop EEG system for phantom limb pain therapy.**
NOVATech × McHacks Buildathon 2026, sponsored by ANT Neuro.

> A research prototype comparing motor-channel EEG covariance with personal movement and
> rest references, then turning that similarity into virtual-hand feedback. Clinical
> benefit and reliable live control have not yet been established.

---

## What this repo contains

| Path | What it is |
|---|---|
| `src/` | The pipeline: contracts, config, data loading, the fidelity score, sources, realtime server |
| `scripts/` | Runnable entry points: setup check, exploration figures, the validation go/no-go, replay demo |
| `ui/` | Research dashboard + rigged GLB hand (locally bundled Three.js, Canvas fallback) |
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
python src/server.py --source sim    # synthetic rehearsal, no download
# open http://127.0.0.1:8766
python src/server.py --source file --subject 4  # curated recorded EEG epochs
```

Live hardware requires verified `--board-id` and `--channel-rows` (12 comma-separated
BrainFlow rows in `config.CHANNELS` order). Confirm these with the mentor first.

See [the review and prioritized plan](docs/10_review-and-next-steps.md) and
[the 3D/Blender guide](docs/11_blender-and-3d.md). The dashboard includes manual exploration,
quality/stale-signal handling, a trace, score integral and CSV session export.

See [how EEG drives the rigged hand](docs/12_eeg-to-hand.md) for the implemented connection,
updated validation results, and hardware-day checklist. EEG-only; no fNIRS.

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