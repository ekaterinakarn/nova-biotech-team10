# 04 — The Fidelity Score (our original contribution)

This is the ~30 lines that are genuinely original in the project. Everything else is a library call;
this is the idea.

## The science it's built on

**ERD (event-related desynchronisation).** When a piece of cortex starts working, its rhythm gets
*weaker*, not stronger. Idling neurons oscillate together, so their fields add up into a big signal;
working neurons do differentiated things at different times, so their fields partly cancel. Activity
looks like a *drop*. Motor imagery suppresses mu (8–12 Hz) over sensorimotor cortex.

**Why we do NOT threshold ERD magnitude.** Kimura et al. (n=20) found subjective imagery vividness
was **not** correlated with ERD magnitude. What *did* correlate (r ≈ −0.69, −0.73) was the
**similarity** between the sensorimotor pattern during *real* movement and during *imagined*
movement. Good imagers don't produce a bigger signal — **they reproduce their own movement
signature.** So we measure similarity to a personal template, not the size of a dip.

**Why it must be direction-agnostic and per-person.** A 2022 study found amputees can show mu power
*increase* during imagery where controls show a decrease — the sign flips. A magnitude threshold
breaks; a *pattern-distance* measure survives, because "how far is this from your movement pattern"
doesn't care which way the power went.

## The representation: covariance, not band-power

For a 2-second window `X` of shape `(n_channels, n_times)`, the raw voltages are mostly noise — the
exact wiggles are never the same twice. What carries the information is **how the channels move
together**. When left motor cortex desynchronises, C3's variance drops relative to C4's, and the
whole correlation structure across the twelve channels shifts in a characteristic way.

The **covariance matrix** captures exactly that: a `12 × 12` grid where entry `(i, j)` is how much
channel `i` and channel `j` co-vary in this window.

```
C = (X @ X.T) / (n_times - 1)      # shape (12, 12), symmetric positive-(semi)definite
```

We regularize it slightly (shrinkage toward the identity) so it is strictly positive-definite (SPD)
and safe to take a matrix logarithm of:

```
C = (1 - a) * C + a * trace(C)/n * I      # a small, e.g. 0.05
```

## The distance: Riemannian, not Euclidean

Covariance matrices live on a curved manifold of SPD matrices, not in flat space. Comparing them
with ordinary Euclidean distance is wrong (it can even produce non-SPD averages). The correct
distance respects the manifold's geometry.

We use the **log-Euclidean distance** (fast, robust, and easy to explain), with the affine-invariant
distance available as a cross-check:

```
d(A, B) = || logm(A) − logm(B) ||_F          # log-Euclidean
```

where `logm` is the symmetric matrix logarithm (via eigendecomposition: log the eigenvalues, rebuild)
and `||·||_F` is the Frobenius norm. Intuition: map both matrices into a flat "log space" where
straight-line distance *is* geometrically correct, then measure it.

**Hybrid implementation (our decision):** we hand-roll `covariance()` and `riemannian_distance()`
from `numpy`/`scipy.linalg` (~15 lines) so we can explain every step, and we cross-check them against
`pyriemann` in `tests/` so we can prove they're correct.

## The score

**Step 1 — record two templates (calibration, ~1–5 min).** Ask the person to actually move (or, for
an amputee, to *attempt* to move the phantom — they still issue the motor command). Then ask them to
rest. Average the covariance matrices from each. Now you have two personal reference patterns:
`C_exec` (your movement) and `C_rest` (your rest).

**Step 2 — measure distance.** For each new 2-second window, compute its covariance `C` and its
distance to each template:

```
d_exec = d(C, C_exec)      # how far from "you moving"
d_rest = d(C, C_rest)      # how far from "you resting"
```

**Step 3 — turn it into one number in [0, 1].**

```
fidelity = d_rest / (d_exec + d_rest)
```

| fidelity | interpretation |
|---|---|
| → 1.0 | looks like your movement pattern (**engaged**) |
| ≈ 0.5 | ambiguous |
| → 0.0 | looks like your rest pattern (**not doing it**) |

It's a ratio, so it's automatically normalized per person and needs no magic threshold.

## Why this is the right design for our audience

- **Entirely within-person** — no need to transfer a model between people, the hardest unsolved
  problem in this field, sidestepped.
- **Direction-agnostic** — "does this match *your* pattern," not "did power go down." Survives the
  amputee sign-flip.
- **Continuous** — drives the hand smoothly, and *adds up over a session into a dose* (integrate
  fidelity over time → the measured dose no clinical trial in this field has ever reported).
- **Few-trials** — a five-minute calibration is all a patient will tolerate.

## The honest caveat

The fidelity score measures *engagement fidelity*, not *pain reduction*. We validate on PhysioNet
that it separates genuine imagery from rest (see `docs/06`), and we cite the therapy literature for
the pain-reduction link. We do not claim to have measured pain.
