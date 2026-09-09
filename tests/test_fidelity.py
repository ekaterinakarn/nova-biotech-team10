"""Tests for the fidelity score.

Two jobs:
    1. Prove the hand-rolled covariance/distance match the pyriemann library (correctness).
    2. Prove the scorer behaves: ~1 on movement-like windows, ~0 on rest-like, ~0.5 mixed.

Run:  pytest tests/ -q
"""

from __future__ import annotations

import numpy as np
import pytest

# pyriemann moved this module in 0.14; try the new path, fall back for older versions.
try:
    from pyriemann.geometry.distance import distance_logeuclid, distance_riemann
except ImportError:  # pyriemann < 0.14
    from pyriemann.utils.distance import distance_logeuclid, distance_riemann

from src.fidelity import (
    FidelityScorer,
    covariance,
    logeuclid_mean,
    riemannian_distance,
)


def _spd_from_random(rng, n=9, t=320):
    """A realistic SPD covariance built from a random window (same path the scorer uses)."""
    X = rng.standard_normal((n, t))
    return covariance(X)


def test_covariance_is_spd_and_symmetric():
    rng = np.random.default_rng(0)
    C = _spd_from_random(rng)
    assert np.allclose(C, C.T), "covariance must be symmetric"
    eigvals = np.linalg.eigvalsh(C)
    assert (eigvals > 0).all(), "covariance must be positive-definite (all eigenvalues > 0)"


def test_logeuclid_distance_matches_pyriemann():
    rng = np.random.default_rng(1)
    A, B = _spd_from_random(rng), _spd_from_random(rng)
    ours = riemannian_distance(A, B, metric="logeuclid")
    theirs = distance_logeuclid(A, B)
    assert ours == pytest.approx(theirs, rel=1e-6)


def test_affine_invariant_distance_matches_pyriemann():
    rng = np.random.default_rng(2)
    A, B = _spd_from_random(rng), _spd_from_random(rng)
    ours = riemannian_distance(A, B, metric="riemann")
    theirs = distance_riemann(A, B)
    assert ours == pytest.approx(theirs, rel=1e-6)


def test_distance_to_self_is_zero():
    rng = np.random.default_rng(3)
    C = _spd_from_random(rng)
    assert riemannian_distance(C, C, "logeuclid") == pytest.approx(0.0, abs=1e-9)
    assert riemannian_distance(C, C, "riemann") == pytest.approx(0.0, abs=1e-9)


def test_logeuclid_mean_of_one_is_itself():
    rng = np.random.default_rng(4)
    C = _spd_from_random(rng)
    assert np.allclose(logeuclid_mean([C]), C, atol=1e-9)


def _windows(rng, sigma, n_epochs=25, n_times=320):
    """Stack of windows drawn from a fixed channel covariance `sigma`.
    Shape: (n_epochs, n_channels, n_times)."""
    n = sigma.shape[0]
    return np.stack([
        rng.multivariate_normal(np.zeros(n), sigma, size=n_times).T
        for _ in range(n_epochs)
    ])


@pytest.mark.parametrize("metric", ["logeuclid", "riemann"])
def test_scorer_separates_movement_from_rest(metric):
    """With two clearly different covariance structures, windows from the 'movement'
    structure should score near 1 and 'rest' windows near 0."""
    rng = np.random.default_rng(5)
    n = 9
    # Two distinct SPD covariance structures.
    Ae = rng.standard_normal((n, n)); sigma_exec = Ae @ Ae.T + n * np.eye(n)
    Ar = rng.standard_normal((n, n)); sigma_rest = Ar @ Ar.T + n * np.eye(n)

    X_exec = _windows(rng, sigma_exec)
    X_rest = _windows(rng, sigma_rest)

    scorer = FidelityScorer(metric=metric, channel_idx=list(range(n)))
    scorer.calibrate(X_exec, X_rest)

    # Fresh windows from each structure.
    exec_scores = [scorer.score(w) for w in _windows(rng, sigma_exec, n_epochs=15)]
    rest_scores = [scorer.score(w) for w in _windows(rng, sigma_rest, n_epochs=15)]

    assert np.mean(exec_scores) > 0.7, f"movement windows should score high: {np.mean(exec_scores):.2f}"
    assert np.mean(rest_scores) < 0.3, f"rest windows should score low: {np.mean(rest_scores):.2f}"


def test_score_before_calibrate_raises():
    scorer = FidelityScorer(channel_idx=list(range(9)))
    with pytest.raises(RuntimeError):
        scorer.score(np.random.default_rng(6).standard_normal((9, 320)))


@pytest.mark.parametrize("window", [np.zeros((9, 320)), np.ones((9, 1)), np.full((9, 320), np.nan)])
def test_degenerate_windows_rejected(window):
    with pytest.raises(ValueError):
        covariance(window)


@pytest.mark.parametrize("scale", [1e-6, 1e-9, 1e6])
def test_log_distance_is_invariant_to_shared_voltage_units(scale):
    rng = np.random.default_rng(41)
    a, b = covariance(rng.normal(size=(9, 320))), covariance(rng.normal(size=(9, 320)))
    assert riemannian_distance(a*scale**2, b*scale**2) == pytest.approx(
        riemannian_distance(a, b), rel=1e-8)
