"""Three interchangeable EEG sources, all matching the Source contract (contracts.py).

    SimSource  — synthetic data; how you demo/test with no hardware and no data files.
    FileSource — replays curated PhysioNet epochs at two seconds per window. THE MAC DEMO.
    LiveSource — BrainFlow -> ANT Neuro eego. Written blind; runs on Windows on Sept 12.

server.py holds one of these and never knows which. Swapping them is one line
(--source sim|file|live), which is the whole point of the seam (docs/02).

Every source provides:
    .fs                     sampling rate (Hz) of the windows it yields
    .calibration_windows()  -> (X_exec, X_rest), each (n_epochs, 12, n_times)
    .stream()               -> yields (12, n_times) windows, one per call
"""

from __future__ import annotations

from typing import Iterator

import numpy as np

from src import config, data


# --------------------------------------------------------------------------- #
# SimSource — synthetic, no hardware, no files.
# --------------------------------------------------------------------------- #
class SimSource:
    """Generates fake 12-channel windows from two distinct covariance structures and
    slowly oscillates between them, so the demo hand opens and closes on its own.
    This is how you unit-test / rehearse a BCI with nothing plugged in."""

    def __init__(self, fs: float = config.FS, seed: int = 0) -> None:
        self.fs = fs
        self.n_times = config.window_samples(fs)
        rng = np.random.default_rng(seed)
        n = config.N_CHANNELS
        # Two random-but-fixed SPD covariance "signatures": movement vs rest.
        Ae = rng.standard_normal((n, n)); self._sigma_exec = Ae @ Ae.T + n * np.eye(n)
        Ar = rng.standard_normal((n, n)); self._sigma_rest = Ar @ Ar.T + n * np.eye(n)
        self._rng = rng
        self._phase = 0.0

    def _draw(self, sigma: np.ndarray) -> np.ndarray:
        """One (12, n_times) window drawn from a given channel covariance."""
        n = sigma.shape[0]
        return self._rng.multivariate_normal(np.zeros(n), sigma, size=self.n_times).T

    def calibration_windows(self) -> tuple[np.ndarray, np.ndarray]:
        X_exec = np.stack([self._draw(self._sigma_exec) for _ in range(30)])
        X_rest = np.stack([self._draw(self._sigma_rest) for _ in range(30)])
        return X_exec, X_rest

    def stream(self) -> Iterator[np.ndarray]:
        # w oscillates 0..1 over ~10 s; a convex mix of two SPD matrices is still SPD.
        while True:
            self._phase += 2 * np.pi * config.STEP_SEC / 10
            w = 0.5 * (1 + np.sin(self._phase))          # 0..1
            sigma = (1 - w) * self._sigma_rest + w * self._sigma_exec
            yield self._draw(sigma)


# --------------------------------------------------------------------------- #
# FileSource — replay a real PhysioNet recording. The Mac demo.
# --------------------------------------------------------------------------- #
class FileSource:
    """Loads one PhysioNet subject: real movement + rest become the calibration
    templates, and the stream alternates that subject's REST and IMAGINED windows so
    the hand visibly rises during imagery and falls during rest — all from real brain
    data, no hardware."""

    def __init__(self, subject: int = 1) -> None:
        self.fs = config.FS
        self._cw = data.condition_windows(subject)
        # Interleave rest and imagery windows into one demo sequence.
        rest, imagery = self._cw["imagery_rest"], self._cw["imagery"]
        seq = []
        for i in range(max(len(rest), len(imagery))):
            if i < len(rest):
                seq.append((rest[i], "recorded rest"))
            if i < len(imagery):
                seq.append((imagery[i], "recorded imagery"))
        self._sequence = seq

    def calibration_windows(self) -> tuple[np.ndarray, np.ndarray]:
        return self._cw["exec"], self._cw["rest"]

    def stream(self) -> Iterator[np.ndarray]:
        # Loop the recorded sequence forever so the demo never runs out.
        while True:
            for window, label in self._sequence:
                self.recorded_condition = label
                yield window


# --------------------------------------------------------------------------- #
# LiveSource — BrainFlow -> ANT Neuro eego. Hardware integration remains unverified.
# --------------------------------------------------------------------------- #
class LiveSource:
    """Live amplifier via BrainFlow. Imports fine on macOS but only STREAMS on
    Windows/Linux (docs/08). Confirm board id, channel map, and sampling rate with the
    ANT Neuro mentor before Sept 12; they're passed in here so nothing is hard-coded."""

    def __init__(
        self,
        board_id: int | None = None,
        serial_port: str = "",
        channel_rows: list[int] | None = None,
        exec_sec: float = 60.0,
        rest_sec: float = 60.0,
    ) -> None:
        # Import lazily so the rest of the project runs on machines without a device.
        from brainflow.board_shim import BoardIds, BoardShim, BrainFlowInputParams

        if board_id is None:
            board_id = BoardIds.ANT_NEURO_EE_410_BOARD.value  # adjust to the provided model

        params = BrainFlowInputParams()
        params.serial_port = serial_port

        self._board = BoardShim(board_id, params)
        self._board_id = board_id
        self.fs = BoardShim.get_sampling_rate(board_id)
        self.n_times = config.window_samples(self.fs)
        self._exec_sec, self._rest_sec = exec_sec, rest_sec

        # Which board rows correspond to our 12 channels. Default to the board's EEG
        # rows; provide channel_rows once the exact eego layout is confirmed.
        eeg_rows = BoardShim.get_eeg_channels(board_id)
        if channel_rows is None:
            raise ValueError("Live EEG requires verified channel_rows in config.CHANNELS order; "
                             "confirm the amplifier and montage with the ANT Neuro mentor")
        if len(channel_rows) != config.N_CHANNELS or len(set(channel_rows)) != config.N_CHANNELS or not set(channel_rows) <= set(eeg_rows):
            raise ValueError("channel_rows must contain 12 unique EEG rows")
        self._rows = channel_rows

        self._board.prepare_session()
        self._board.start_stream()

    def _grab(self, n: int, filtered: bool = True) -> np.ndarray:
        """Newest n samples on our 12 channels -> (12, n)."""
        buf = self._board.get_current_board_data(n)   # (n_rows, n)
        raw = buf[self._rows, :]
        if not filtered or raw.shape[1] < self.n_times:
            return raw
        return self._filter(raw)

    def _filter(self, raw):
        # Identical window filtering for live calibration and inference. This is a
        # windowed IIR approximation, not the offline continuous MNE FIR filter.
        from scipy.signal import butter, sosfiltfilt, iirnotch, filtfilt
        if self.fs > 2 * config.NOTCH_HZ:
            b, a = iirnotch(config.NOTCH_HZ, 30, self.fs)
            raw = filtfilt(b, a, raw, axis=-1)
        sos = butter(4, config.BAND_HZ, btype="bandpass", fs=self.fs, output="sos")
        return sosfiltfilt(sos, raw, axis=-1)

    def _collect(self, seconds: float) -> np.ndarray:
        """Block for `seconds`, then cut the buffer into 2-second windows -> (n, 12, t)."""
        import time
        time.sleep(seconds)
        raw = self._grab(int(seconds * self.fs), filtered=False)       # (12, seconds*fs)
        step = self.n_times
        windows = [self._filter(raw[:, i:i + step]) for i in range(0, raw.shape[1] - step + 1, step)]
        return np.stack(windows) if windows else np.empty((0, config.N_CHANNELS, step))

    def calibration_windows(self) -> tuple[np.ndarray, np.ndarray]:
        print(f"CALIBRATION: attempt to MOVE for {self._exec_sec:.0f}s...")
        X_exec = self._collect(self._exec_sec)
        print(f"CALIBRATION: now REST for {self._rest_sec:.0f}s...")
        X_rest = self._collect(self._rest_sec)
        return X_exec, X_rest

    def stream(self) -> Iterator[np.ndarray]:
        import time
        while True:
            window = self._grab(self.n_times)
            if window.shape[1] == self.n_times:
                yield window
            else:
                time.sleep(config.STEP_SEC)

    def close(self):
        """Release amplifier resources on exit."""
        try:
            self._board.stop_stream()
        finally:
            self._board.release_session()


# --------------------------------------------------------------------------- #
def make_source(kind: str, subject: int = 1, **live_options):
    """Factory used by server.py: map a --source string to a Source instance."""
    if kind == "sim":
        return SimSource()
    if kind == "file":
        return FileSource(subject=subject)
    if kind == "live":
        return LiveSource(**live_options)
    raise ValueError(f"unknown source {kind!r} (use sim|file|live)")
