"""Conservative window screening; thresholds are heuristics, not artifact diagnosis."""
import numpy as np
from src import config


class QualityGate:
    """Compare (12, time) channel variances to a calibration median in source units."""
    def __init__(self, epochs):
        self.reference = np.median(np.var(epochs, axis=-1), axis=0)
        # Channel count comes from the calibration data, so the gate works for any
        # montage (12-lead eego, 8-channel Unicorn, ...), not just config.N_CHANNELS.
        self.n_channels = self.reference.shape[0]
        if not np.isfinite(self.reference).all() or np.any(self.reference <= 0):
            raise ValueError("Calibration contains flat/non-finite channels; repeat calibration")

    def check(self, window):
        if window.ndim != 2 or window.shape[0] != self.n_channels or window.shape[1] < 2:
            return False
        if not np.isfinite(window).all():
            return False
        variance = np.var(window, axis=1)
        ratio = variance / self.reference
        centered = window - window.mean(axis=1, keepdims=True)
        kurtosis = np.mean(centered ** 4, axis=1) / np.maximum(variance ** 2, np.finfo(float).tiny)
        return bool(np.all((ratio > config.QUALITY_MIN_RATIO) &
                           (ratio < config.QUALITY_MAX_RATIO)) and
                    np.all(kurtosis < config.QUALITY_MAX_KURTOSIS))
