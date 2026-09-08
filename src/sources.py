"""Three interchangeable EEG sources, all matching the Source contract (contracts.py).

    SimSource  — synthetic data; how you demo/test with no hardware and no data files.
    FileSource — replays a real PhysioNet recording at true speed. THE MAC DEMO.
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
            self._phase += 0.03
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
                seq.append(rest[i])
            if i < len(imagery):
                seq.append(imagery[i])
        self._sequence = seq

    def calibration_windows(self) -> tuple[np.ndarray, np.ndarray]:
        return self._cw["exec"], self._cw["rest"]

    def stream(self) -> Iterator[np.ndarray]:
        # Loop the recorded sequence forever so the demo never runs out.
        while True:
            for window in self._sequence:
                yield window


# --------------------------------------------------------------------------- #
# LiveSource — BrainFlow -> ANT Neuro eego. Written blind, tested on Windows.
# --------------------------------------------------------------------------- #
class LiveSource:
    """Live amplifier via BrainFlow. Imports fine on macOS but only STREAMS on
    Windows/Linux (docs/08). Confirm board id, channel map, and sampling rate with the
    ANT Neuro mentor before Sept 12; they're passed in here so nothing is hard-coded."""

    def __init__(
        self,
        board_id: int | None = None,
        serial_port: str = "",
        channel_names: list[str] | None = None,
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
        # rows; override channel_names once the exact eego layout is confirmed.
        eeg_rows = BoardShim.get_eeg_channels(board_id)
        self._rows = eeg_rows[: config.N_CHANNELS]

        self._board.prepare_session()
        self._board.start_stream()

    def _grab(self, n: int) -> np.ndarray:
        """Newest n samples on our 12 channels -> (12, n)."""
        buf = self._board.get_current_board_data(n)   # (n_rows, n)
        return buf[self._rows, :]

    def _collect(self, seconds: float) -> np.ndarray:
        """Block for `seconds`, then cut the buffer into 2-second windows -> (n, 12, t)."""
        import time
        time.sleep(seconds)
        raw = self._grab(int(seconds * self.fs))       # (12, seconds*fs)
        step = self.n_times
        windows = [raw[:, i:i + step] for i in range(0, raw.shape[1] - step, step)]
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
            yield self._grab(self.n_times)
            time.sleep(config.WINDOW_SEC * config.STEP_SEC / config.WINDOW_SEC)


# --------------------------------------------------------------------------- #
def make_source(kind: str, subject: int = 1):
    """Factory used by server.py: map a --source string to a Source instance."""
    if kind == "sim":
        return SimSource()
    if kind == "file":
        return FileSource(subject=subject)
    if kind == "live":
        return LiveSource()
    raise ValueError(f"unknown source {kind!r} (use sim|file|live)")
