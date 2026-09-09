# 07 — Pitch Deck Outline (`10_buildathon.pptx` + `.pdf`)

> September 8 review: see [current implementation, evidence caveats and priorities](10_review-and-next-steps.md). Historical claims and task statuses below are not all verified.

The deck must cover these sections (in any order). Build it in Canva, export as **both** `.pptx`
and `.pdf`, named `10_buildathon`.

## Suggested flow (10–12 slides)

1. **Hook / title** — "Reading a Phantom Hand." The 90-second demo promise.
2. **The problem** — phantom limb pain in ~60% of amputees; therapies exist but the evidence is a
   mess because **nobody measured whether the patient was doing the exercise.** The unmeasured dose.
3. **The insight** — motor imagery is invisible; EEG makes it visible. *EEG is the instrument, not
   the drug.*
4. **How ANT Neuro's EEGgo / eego works** — amplifier, differential amplification & common-mode
   rejection, electrode setup, impedance, sampling, 10/20 placement. (See `docs/08_hardware-live.md`.)
5. **The algorithm** — the pipeline (Source → filter → windows → covariance → fidelity). The fidelity
   score explained simply: distance to *your* movement vs *your* rest, `d_rest/(d_exec+d_rest)`.
   One equation, one diagram.
6. **Why it's trustworthy** — CSP topomap over motor cortex, permutation test, the occipital-leak
   fix with its accuracy delta. Real numbers: validation p-value + kappa; 73.3% CSP baseline.
7. **Difficulties & how they were solved** — occipital leak (Oz alpha) → excluded Fz/Pz/Oz; amputee
   ERD sign-flip → direction-agnostic distance; Mac can't run the amplifier → Source seam +
   FileSource; T1/T2 run-map trap → explicit mapping.
8. **Demo** — the live 5-condition sequence (squeeze/imagine/watch/math/feel) with the fidelity bar,
   then the sham toggle. (See `docs/06`.)
9. **Application & impact** — a dosimeter for motor-imagery therapy; who benefits (amputees,
   clinicians, trialists); why measurement is the unlock.
10. **Business plan & revenue** — **measurement device before therapy device → far lower regulatory
    bar.** First customers already exist: the researchers running these trials who cannot measure
    adherence today. Target market, pricing, projected streams. (See below.)
11. **Future directions** — amputee validation study, left/right stretch goal, rigged glTF hand,
    session-dose analytics, the sham-controlled trial to run next.
12. **Close** — the one-line ask.

## Business plan seeds (R5 — make them concrete with numbers)

- **Wedge:** a research/clinical **measurement tool** (adherence + dose for motor-imagery therapy),
  not a treatment claim → Class I / research-use pathway, far cheaper and faster than a therapy device.
- **First customers:** rehab researchers and PLP clinics running mirror/MI/VR trials who currently
  report dose as "10 sessions × 2 hours" (i.e. not a dose at all). Sell them the missing dependent
  variable.
- **Later:** licensed home-therapy add-on bundled with existing MI/VR therapy platforms.
- **Numbers to fill in:** amputee population & PLP prevalence (~60%), # of active MI/rehab trials,
  price per site / per subject-session, addressable rehab-clinic count. Source real figures for the
  projection.
