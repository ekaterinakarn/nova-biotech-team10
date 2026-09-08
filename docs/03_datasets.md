# 03 — Datasets

## Primary: PhysioNet EEG Motor Movement/Imagery (EEGMMIDB)

- **109 subjects**, 64 channels, **160 Hz**, EDF+ format.
- Free, one-line download: `mne.datasets.eegbci.load_data(subject, runs)`.
- Homepage: https://physionet.org/content/eegmmidb/1.0.0/
- Why it's perfect for us: it contains the *same people* doing **real** movement and then
  **imagining** the same movement — an execution template and an imagery test condition, already
  recorded. That is exactly what the fidelity score needs to be validated *before* we touch hardware.

### The run map — the #1 silent bug in EEG code

`T1`/`T2` mean **different things in different runs**. Get this wrong and your labels are garbage but
nothing errors.

| Runs | Task | T0 | T1 | T2 |
|---|---|---|---|---|
| 3, 7, 11 | **Real** movement | rest | left fist | right fist |
| 4, 8, 12 | **Imagined** movement | rest | left fist | right fist |
| 5, 9, 13 | Real | rest | both fists | both feet |
| 6, 10, 14 | Imagined | rest | both fists | both feet |

`T0` = rest in every run. **The pairing that matters: runs 3/7/11 (real) and 4/8/12 (imagined) are
the same people doing then imagining left/right fist.** Runs 1–2 are baselines (eyes open/closed).

Commonly excluded subjects (known bad recordings): **88, 89, 92, 100, 104**.

### The channel-name gotcha (handle in `data.py`)

EEGMMIDB stores channel names with trailing dots and non-standard case, e.g. `Fc3.`, `C3..`,
`Cz..`, `Cp3.`, `Fz..`, `Oz..`. If you try to pick `"C3"` or set a montage directly, it silently
mismatches. The fix is one line, **called before montage/picking**:

```python
mne.datasets.eegbci.standardize(raw)   # 'Fc3.' -> 'FC3', 'C3..' -> 'C3', etc.
raw.set_montage("standard_1005")
```

### Our 12 channels

```
FC3 FC4 · C3 C1 Cz C2 C4 · CP3 CP4 · Fz Pz Oz
```

- **Motor core + Laplacian ring** (FC3/FC4, C3/C1/Cz/C2/C4, CP3/CP4): where mu/beta ERD lives.
- **Fz** — frontal-midline theta, a proxy for cognitive effort (fatigue branch).
- **Pz** — parietal, engagement/attention.
- **Oz** — occipital, an eyes-open sanity check (and the source of the known CSP leak, below).

**Classifier input excludes Fz/Pz/Oz** (the occipital-leak fix — see below); those three feed the
fatigue/effort branch only.

### Known issue: the occipital CSP leak

An early CSP topomap showed the strongest learned filter as a blob at the **back** of the head — the
model was partly reading occipital alpha through Oz, not motor cortex. Fix: **exclude Fz/Pz/Oz from
the classifier/fidelity input**, keep them for the fatigue branch, and **report the accuracy
difference** — honest science, and it confirms the model reads motor cortex rather than occipital alpha.

## Reference only: amputee dataset (do NOT train on pain)

- **OpenNeuro ds006921** — 13 amputees with phantom limb pain, 6 without, 19 controls, pre-registered.
- Finding: **no** pain-specific oscillatory markers. We cite this to explain *why we do not build
  pain detection* — claiming to detect phantom pain from EEG would be indefensible in Q&A.
- No open **motor-imagery** EEG data from amputees exists, which is why we validate on PhysioNet
  and state the amputee-transfer limitation honestly.

## Sampling-rate note (PhysioNet vs live eego)

PhysioNet is 160 Hz; the ANT Neuro eego samples much faster (commonly 500–2000 Hz). `config.FS`
drives the window length and filter design, so the offline and live paths each use their own `FS`.
Because the fidelity score **calibrates per session on the same source**, exec/rest/test windows are
always at one consistent sampling rate — no cross-rate template mismatch. See `docs/08_hardware-live.md`.

## Citations to keep handy

- Kimura et al. — ERD *magnitude* did **not** correlate with imagery vividness; *pattern similarity*
  between real and imagined movement did (r ≈ −0.69, −0.73). Basis of the fidelity score.
- 2022 study — amputees can show mu power **increase** during imagery (ERD sign-flip). Basis of the
  direction-agnostic design.
- 2023 review (placebo-controlled mirror therapy) — no evidence of efficacy → the measurement gap.
- 2024 RCT (n=80) — decoded execution no better than plain imagery → still no dose measured.
