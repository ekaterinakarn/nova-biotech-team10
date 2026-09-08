"""NeuroLoop — closed-loop EEG pipeline for motor-imagery fidelity scoring.

Package layout (see docs/02_architecture.md):
    contracts  — the frozen seams: Source, FidelityScorer, Frame
    config     — every constant in one place
    data       — PhysioNet loading, filtering, epoching -> (n, 12, n_times) arrays
    fidelity   — the original contribution: per-person Riemannian fidelity score
    sources    — SimSource / FileSource / LiveSource (interchangeable)
    server     — realtime loop, emits Frame JSON over WebSocket at 20 Hz
"""
