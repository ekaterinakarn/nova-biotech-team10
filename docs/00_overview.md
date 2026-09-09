# 00 — Project Overview

> September 8 review: see [current implementation, evidence caveats and priorities](10_review-and-next-steps.md). Historical claims and task statuses below are not all verified.

## One-sentence pitch

A 12-channel closed-loop system that measures whether the user is **genuinely engaging their
motor cortex**, scored against their own attempted-movement signature, driving a virtual hand on
screen. It turns an invisible, unverifiable therapy into a **measurable dose**.

## The problem, in one paragraph

~60% of amputees get phantom limb pain (lifetime prevalence 76–87%). Motor-imagery therapies
(mirror therapy, motor imagery, VR phantom execution) help — a 2024 multicentre RCT (n=80) found
~65% pain reduction — but the evidence is a mess: a 2023 review restricted to *placebo-controlled*
mirror-therapy trials found, in its own title, **no evidence of efficacy**. The hole in every one
of those studies: **nobody measured whether the patient was actually doing the exercise.** Motor
imagery is invisible — a clinician watching a patient sit still with eyes closed cannot tell a
genuine fist-clench imagination from someone thinking about lunch. Every trial in this literature
has an *unmeasured dose*. That is a measurement problem, and it is the one this project addresses.

## Framing

**EEG is the instrument, not the drug.** This is not a claim to cure pain or to have invented a
therapy. It is a **dosimeter** the field lacks — the instrument that would let someone finally test
the therapy properly, and deliver it outside a hospital while they do. That is a smaller claim and
a far more defensible one.

## What we are building (the loop)

A person wears a 12-electrode cap. The software reads their brain activity, compares it against a
short recording of *that same person genuinely attempting to move*, and produces one number:
**are you really engaging your motor cortex right now, and how well?** A virtual arm on screen
moves in proportion to that number. When the number drops, the system notices and coaches. When it
rises, the arm responds. That feedback loop is the therapy delivery mechanism *and* the measurement.

- **The arm** gives the brain the coherent visual feedback that makes the therapy work (mirror
  therapy, in software).
- **The score** measures whether the person is genuinely doing the exercise, second by second.
- **The loop** uses the score to adapt what the system asks of them (the closed loop, requirement R4).

## What we can and cannot claim

| Can claim | Cannot claim |
|---|---|
| We measure motor-cortex engagement, per person, in real time | That it reduces phantom limb pain (out of scope; the therapy family is supported by cited studies) |
| The score is direction-agnostic and survives the amputee ERD sign-flip | That it works on amputees specifically — no open motor-imagery EEG data from amputees exists |
| We can distinguish genuine kinesthetic imagery from visual imagery, rest, and artifacts | To detect phantom pain from EEG — OpenNeuro ds006921 found **no** pain-specific markers |

Stating the limits plainly is more trustworthy than claiming a cure, and it sets up the future-work
/ clinical-trial direction.

See [`05_build-plan.md`](05_build-plan.md) for the file-by-file order and timeline.
