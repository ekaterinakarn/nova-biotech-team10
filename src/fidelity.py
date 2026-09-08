"""The fidelity score — the project's original contribution (see docs/04_fidelity-design.md).

The idea in one line: measure how much a 2-second window looks like *your own* movement
pattern versus *your own* rest pattern, where "pattern" means the channel covariance
matrix and "looks like" means Riemannian distance on the manifold of covariance matrices.

    fidelity = d_rest / (d_exec + d_rest)     # 1 = engaged, 0.5 = ambiguous, 0 = resting

Everything here is hand-rolled from numpy/scipy so every line is explainable; tests/
cross-check the covariance and distance against the pyriemann library.

Array shapes:
    X   : (n_channels, n_times)          one window
    C   : (n_channels, n_channels)       its covariance (symmetric positive-definite, SPD)
"""

from __future__ import annotations

import numpy as np
from scipy.linalg import eigvalsh

from src import config


# --------------------------------------------------------------------------- #
# Covariance and matrix functions (hand-rolled).
# --------------------------------------------------------------------------- #
def covariance(X: np.ndarray, shrinkage: float = config.SHRINKAGE) -> np.ndarray:
    """Sample covariance of a window, regularized to stay strictly SPD.

    Args:
        X:         (n_channels, n_times) — one window.
        shrinkage: pull toward a scaled identity by this fraction (0..1). Keeps the
                   matrix invertible / safe to take a log of even with few samples.
    Returns:
        C: (n_channels, n_channels) symmetric positive-definite covariance.
    """
    Xc = X - X.mean(axis=1, keepdims=True)          # centre each channel (row)
    C = (Xc @ Xc.T) / (Xc.shape[1] - 1)             # unbiased sample covariance
    if shrinkage > 0:
        mu = np.trace(C) / C.shape[0]               # average variance
        C = (1 - shrinkage) * C + shrinkage * mu * np.eye(C.shape[0])
    return C


def _logm_spd(C: np.ndarray) -> np.ndarray:
    """Symmetric matrix logarithm of an SPD matrix, via its eigendecomposition:
    log the eigenvalues, rebuild. (C = V diag(w) V.T  ->  log C = V diag(log w) V.T.)"""
    w, V = np.linalg.eigh(C)
    w = np.clip(w, 1e-12, None)                     # guard tiny/negative eigenvalues
    return (V * np.log(w)) @ V.T


def _expm_spd(S: np.ndarray) -> np.ndarray:
    """Inverse of _logm_spd: symmetric matrix exponential (exp the eigenvalues)."""
    w, V = np.linalg.eigh(S)
    return (V * np.exp(w)) @ V.T


def riemannian_distance(A: np.ndarray, B: np.ndarray, metric: str = config.RIEMANN_METRIC) -> float:
    """Distance between two SPD covariance matrices on their curved manifold.

    "logeuclid" (default): map both into flat log-space and measure straight-line
        (Frobenius) distance there:  || log A - log B ||_F.  Fast, robust, easy to explain.
    "riemann" (affine-invariant): the true geodesic distance,
        sqrt(sum_i log(lambda_i)^2) where lambda_i are the eigenvalues of A^-1 B
        (obtained as the generalized eigenvalues of (B, A)). Used as a cross-check.
    """
    if metric == "logeuclid":
        return float(np.linalg.norm(_logm_spd(A) - _logm_spd(B), ord="fro"))
    if metric == "riemann":
        lam = eigvalsh(B, A)                         # generalized eigenvalues of A^-1 B
        lam = np.clip(lam, 1e-12, None)
        return float(np.sqrt(np.sum(np.log(lam) ** 2)))
    raise ValueError(f"unknown metric {metric!r} (use 'logeuclid' or 'riemann')")


def logeuclid_mean(covs: list[np.ndarray]) -> np.ndarray:
    """Average of SPD matrices done correctly: mean in log-space, mapped back.
    exp( mean_i log C_i ). A plain elementwise average is wrong on this manifold."""
    log_mean = np.mean([_logm_spd(C) for C in covs], axis=0)
    return _expm_spd(log_mean)


# --------------------------------------------------------------------------- #
# The scorer (implements the FidelityScorer contract).
# --------------------------------------------------------------------------- #
class FidelityScorer:
    """Per-person, direction-agnostic fidelity scorer.

    Lifecycle:
        scorer = FidelityScorer()
        scorer.calibrate(X_exec, X_rest)   # once per session, from a short calibration
        value = scorer.score(X_window)     # for each new 2-second window

    By default it scores on the 9 MOTOR channels only (config.MOTOR_IDX) — the
    occipital-leak fix from docs/03, so the score can't cheat via Oz alpha. Pass
    channel_idx explicitly (e.g. list(range(n))) to score on all channels, as tests do.
    """

    def __init__(
        self,
        metric: str = config.RIEMANN_METRIC,
        shrinkage: float = config.SHRINKAGE,
        channel_idx: list[int] | None = None,
    ) -> None:
        self.metric = metric
        self.shrinkage = shrinkage
        self.channel_idx = config.MOTOR_IDX if channel_idx is None else channel_idx
        self.C_exec: np.ndarray | None = None   # movement template (SPD)
        self.C_rest: np.ndarray | None = None   # rest template (SPD)

    def _cov(self, X: np.ndarray) -> np.ndarray:
        """Covariance of a window restricted to the scorer's channels."""
        return covariance(X[self.channel_idx, :], self.shrinkage)

    def calibrate(self, X_exec: np.ndarray, X_rest: np.ndarray) -> None:
        """Build the two personal templates from calibration windows.

        Args:
            X_exec, X_rest: (n_epochs, n_channels, n_times) movement and rest windows.
        """
        self.C_exec = logeuclid_mean([self._cov(x) for x in X_exec])
        self.C_rest = logeuclid_mean([self._cov(x) for x in X_rest])

    def distances(self, X_window: np.ndarray) -> tuple[float, float]:
        """Return (d_exec, d_rest): distance from this window to each template."""
        if self.C_exec is None or self.C_rest is None:
            raise RuntimeError("call calibrate() before score()/distances()")
        C = self._cov(X_window)
        return (riemannian_distance(C, self.C_exec, self.metric),
                riemannian_distance(C, self.C_rest, self.metric))

    def score(self, X_window: np.ndarray) -> float:
        """Fidelity in [0, 1]: ~1 looks like movement, ~0 looks like rest, ~0.5 ambiguous."""
        d_exec, d_rest = self.distances(X_window)
        total = d_exec + d_rest
        if total <= 0:                       # identical to both templates (degenerate)
            return 0.5
        return float(np.clip(d_rest / total, 0.0, 1.0))
