# 08 — Hardware & Live Runbook (ANT Neuro eego / EEGgo)

Backs the "how ANT Neuro's EEGgo works" section and the Sept 12 live-day plan.

## How the amplifier turns brain into numbers

1. **Electrodes (10/20 system).** Small discs on the scalp at standardized positions (F=frontal,
   C=central, P=parietal, O=occipital, subscript z=midline, odd=left, even=right). Gel lowers
   **impedance** (aim ≤ 5 kΩ) so we record low-resistance through skin.
2. **Differential amplification + common-mode rejection.** Each channel measures the *difference*
   between two electrodes. Noise common to both (mains hum, distant interference) subtracts out;
   only local brain activity, which differs between positions, is amplified (gain ×1,000–100,000).
   This is why EEG works outside a Faraday cage.
3. **Filtering.** Hardware band-pass (~0.1–100 Hz) removes drift and high-frequency muscle/EMI; a
   **notch at 60 Hz** (North America — *not* 50 Hz) removes mains hum.
4. **ADC / sampling.** The analog voltage is sampled above the Nyquist rate (2× highest frequency of
   interest) and converted to a 16-bit integer (e.g. ±10 V range → 20 V / 65,536 ≈ 0.305 mV/level).
   Sampling too slow → **aliasing** (high frequencies masquerade as low).
5. **Stream out.** The eego streams timestamped multichannel samples to software (LSL or BrainFlow).

## The OS constraint (the reason for the Source seam)

**BrainFlow's ANT Neuro backend is Windows/Linux only.** On macOS `brainflow` imports fine but
cannot open the eego device. Consequences:

- **Development + the primary demo run on any laptop** (incl. the M4) via `SimSource`/`FileSource`.
- **The live amplifier runs on the Windows laptop** on Sept 12. Same `server.py`, same `ui/`; only
  `--source live` changes.

## `LiveSource` plan (written blind now, tested on Windows)

`src/sources.py::LiveSource` wraps BrainFlow:

```
BoardShim(BoardIds.ANT_NEURO_*_BOARD, params) → prepare_session() → start_stream()
   → get_current_board_data(n) each tick → pick our 12 channels → yield (12, n_times) window
```

Parameters to confirm with the ANT Neuro mentor on Discord **before** build day:
- exact `BoardId` for the provided eego model, and the serial/IP in `BrainFlowInputParams`;
- the device **sampling rate** (sets `config.FS` for the live path and the window length);
- the **channel order/index map** so we pick FC3…Oz correctly from the board's row layout;
- units (µV vs counts) and any scaling.

## Live-day runbook (Sept 12)

1. On the **Windows** laptop: `pip install -r requirements.txt`, `python scripts/00_setup_check.py`.
2. Cap fitting: gel, get all 12 impedances ≤ ~5 kΩ (bad channels = flat/garbage fidelity).
3. `python src/server.py --source live` → open `ui/index.html`.
4. **Calibrate on a volunteer:** ~1–2 min "attempt to move" (exec) + ~1–2 min rest → templates.
5. Run the 5-condition demo (`docs/06`); tune smoothing α if the hand is jittery/laggy.
6. **Immediately record a backup video** of a good run, in case the hardware flakes.
7. Fallback ladder if anything fails: live → FileSource (real recording) → SimSource. All full demos.

## Impedance / quality gate

`Frame.signal_ok` should reflect channel quality; grey out the hand when a channel is bad rather than
showing a confident-but-wrong number. Honest failure beats a fake success.
