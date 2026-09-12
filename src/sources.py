"""Interchangeable EEG sources, all matching the Source contract (contracts.py).

    SimSource  — synthetic data; how you demo/test with no hardware and no data files.
    FileSource — replays curated PhysioNet epochs at two seconds per window. THE MAC DEMO.
    LiveSource — BrainFlow -> ANT Neuro eego. Streams on Windows/Linux only.
    LslSource  — Lab Streaming Layer inlet; cross-platform, incl. macOS. Pulls the eego
                 (or g.tec Unicorn) over the network by CHANNEL LABEL. See docs/15.

server.py holds one of these and never knows which. Swapping them is one line
(--source sim|file|live|lsl), which is the whole point of the seam (docs/02).

Every source provides:
    .fs                     sampling rate (Hz) of the windows it yields
    .calibration_windows()  -> (X_exec, X_rest), each (n_epochs, n_channels, n_times)
    .stream()               -> yields (n_channels, n_times) windows, one per call
Live/LSL sources also expose .motor_idx (which channels the scorer reads) so montages
with fewer channels than our 12-lead default still work.
"""

from __future__ import annotations

from pathlib import Path
from typing import Iterator

import numpy as np

from src import config, data


def window_filter(raw: np.ndarray, fs: float) -> np.ndarray:
    """Notch 60 Hz + band-pass 8-30 Hz on one window (n_channels, n_times).

    A windowed IIR (filtfilt) filter, applied identically to calibration and inference
    windows so the covariance features are consistent. This is what makes the LIVE path
    match the offline science (docs/09) — raw amplifier data must be filtered before it
    reaches the scorer, exactly like the PhysioNet path filters in data.py.
    """
    from scipy.signal import butter, sosfiltfilt, iirnotch, filtfilt
    if fs > 2 * config.NOTCH_HZ:
        b, a = iirnotch(config.NOTCH_HZ, 30, fs)
        raw = filtfilt(b, a, raw, axis=-1)
    sos = butter(4, config.BAND_HZ, btype="bandpass", fs=fs, output="sos")
    return sosfiltfilt(sos, raw, axis=-1)


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
# LslSource — Lab Streaming Layer inlet. The cross-platform path onto the Mac.
# --------------------------------------------------------------------------- #
class LslSource:
    """Pull EEG from an LSL outlet on the network (works on macOS, unlike BrainFlow's
    eego backend). Picks our montage channels FROM THE STREAM BY LABEL, so it adapts to
    the eego 24 (a subset of the 64) or the 8-channel Unicorn without code changes; a
    missing channel raises a clear error listing what the stream actually offers.

    Both the recording laptop (running the outlet) and this Mac must be on the same
    network; firewalls / blocked multicast are the usual failure. See docs/15."""

    def __init__(
        self,
        montage: str = "eego",
        channels: list[str] | None = None,
        stream_name: str | None = None,
        stream_type: str = "EEG",
        exec_sec: float = 45.0,
        rest_sec: float = 45.0,
        resolve_timeout: float = 90.0,
    ) -> None:
        import time as _time

        from pylsl import StreamInlet, resolve_streams

        # Target channels: an explicit --lsl-channels list wins, else the named montage.
        self.channel_names = channels if channels else config.MONTAGES[montage]
        self.motor_idx = config.motor_indices(self.channel_names)
        if not self.motor_idx:
            raise ValueError(f"Montage {self.channel_names} has no motor channels "
                             f"(need some of {sorted(config.MOTOR_SITES)})")

        # Find the stream. resolve_streams() is the most reliable resolver with a
        # KnownPeers direct link (LSL discovery over a phone hotspot is slow and flaky),
        # so retry it until the stream appears or we hit resolve_timeout.
        infos = []
        deadline = _time.monotonic() + resolve_timeout
        while not infos and _time.monotonic() < deadline:
            alls = resolve_streams(wait_time=5.0)
            if stream_name:
                infos = [s for s in alls if s.name() == stream_name]
            else:
                infos = [s for s in alls if s.type() == stream_type]
        if not infos:
            raise RuntimeError("No LSL stream found. Is the outlet running and on the same "
                               "network? Firewall / blocked multicast can hide it (docs/15).")

        self._inlet = StreamInlet(infos[0], max_buflen=60)
        info = self._inlet.info()
        self.fs = info.nominal_srate() or config.FS
        self.n_times = config.window_samples(self.fs)
        self._exec_sec, self._rest_sec = exec_sec, rest_sec

        # Map each of our channels to a column in the stream, matched by label.
        stream_labels = self._read_labels(info)
        lut = {lab.strip().upper(): i for i, lab in enumerate(stream_labels)}
        missing = [c for c in self.channel_names if c.upper() not in lut]
        if not missing:
            self._pick = [lut[c.upper()] for c in self.channel_names]
        elif len(stream_labels) >= len(self.channel_names):
            # Blank/generic labels (e.g. the g.tec Unicorn's LSL output, which streams its
            # 8 EEG channels first, then a trailing counter). Map our montage to the FIRST
            # N channels in the montage's known electrode order.
            print(f"WARNING: stream labels {stream_labels} don't match montage names; "
                  f"mapping the first {len(self.channel_names)} channels BY POSITION as "
                  f"{self.channel_names}. Verify the electrode order!")
            self._pick = list(range(len(self.channel_names)))
        else:
            raise RuntimeError(f"Stream is missing montage channels {missing}. "
                               f"Available: {stream_labels}. Use --lsl-channels to match.")
        self._buf = np.zeros((len(self.channel_names), 0))
        print(f"LSL: '{info.name()}' @ {self.fs:.0f} Hz -> {len(self.channel_names)} channels "
              f"({montage}); {len(self.motor_idx)} motor")

    @staticmethod
    def _read_labels(info) -> list[str]:
        """Channel labels from the LSL stream description (blank -> use indices)."""
        labels, ch = [], info.desc().child("channels").child("channel")
        for _ in range(info.channel_count()):
            labels.append(ch.child_value("label"))
            ch = ch.next_sibling()
        return labels if any(labels) else [str(i) for i in range(info.channel_count())]

    def _pull(self, max_samples: int) -> np.ndarray:
        """Pull available samples, return picked channels as (n_channels, n_new)."""
        samples, _ = self._inlet.pull_chunk(timeout=1.0, max_samples=max_samples)
        if not samples:
            return np.zeros((len(self.channel_names), 0))
        return np.asarray(samples).T[self._pick, :]

    def calibration_windows(self) -> tuple[np.ndarray, np.ndarray]:
        import time

        def collect(seconds: float) -> np.ndarray:
            buf = np.zeros((len(self.channel_names), 0))
            end = time.monotonic() + seconds
            while time.monotonic() < end:
                buf = np.concatenate([buf, self._pull(int(self.fs * 2))], axis=1)
            step = self.n_times
            wins = [window_filter(buf[:, i:i + step], self.fs)
                    for i in range(0, buf.shape[1] - step + 1, step)]
            return (np.stack(wins) if wins
                    else np.empty((0, len(self.channel_names), step)))

        print(f"CALIBRATION: attempt to MOVE for {self._exec_sec:.0f}s...")
        X_exec = collect(self._exec_sec)
        print(f"CALIBRATION: now REST for {self._rest_sec:.0f}s...")
        X_rest = collect(self._rest_sec)
        return X_exec, X_rest

    def stream(self) -> Iterator[np.ndarray]:
        while True:
            # ALWAYS pull fresh samples each tick so the window slides forward with new
            # data. (Only topping up "until full" froze the live hand once the buffer
            # filled, because it then stopped pulling and yielded the same stale window.)
            new = self._pull(int(self.fs * 2))
            if new.shape[1]:
                self._buf = np.concatenate([self._buf, new], axis=1)
            keep = self.n_times * 3
            if self._buf.shape[1] > keep:
                self._buf = self._buf[:, -keep:]
            if self._buf.shape[1] < self.n_times:
                continue                      # not enough samples for a window yet
            yield window_filter(self._buf[:, -self.n_times:], self.fs)

    def close(self):
        try:
            self._inlet.close_stream()
        except Exception:
            pass


# --------------------------------------------------------------------------- #
# CntSource — replay a recorded ANT eego .cnt session through the website.
# --------------------------------------------------------------------------- #
class CntSource:
    """Replay a recorded ANT eego .cnt session so the website shows what the brain did.

    Calibrates on the '1001/Hand squeezing' markers vs a rest baseline, then streams the
    session chronologically. Needs the `antio` package (mne.io.read_raw_ant)."""

    def __init__(
        self,
        cnt_file: str,
        channels: tuple[str, ...] = ("C3", "Cz"),
        rest_window: tuple[float, float] = (130.0, 158.0),
        start_sec: float = 148.0,   # ~12 s of baseline, then the marked task at ~160 s
        exec_label: str = "1001/Hand squeezing",
    ) -> None:
        import mne

        raw = mne.io.read_raw_ant(cnt_file, preload=True, verbose="ERROR")
        raw.pick(list(channels))
        raw.notch_filter(config.NOTCH_HZ, verbose="ERROR")
        raw.filter(config.BAND_HZ[0], config.BAND_HZ[1], verbose="ERROR")
        self.fs = raw.info["sfreq"]
        self.n_times = config.window_samples(self.fs)
        self.channel_names = list(channels)
        self.motor_idx = config.motor_indices(self.channel_names)
        self._data = raw.get_data()             # (n_ch, n_times), already filtered
        self._ann = raw.annotations
        self._exec_label = exec_label
        self._rest_window = rest_window
        self._start = int(start_sec * self.fs)
        self.recorded_condition = ""
        print(f"CNT: {Path(cnt_file).name} @ {self.fs:.0f} Hz -> {self.channel_names} "
              f"({len(self.motor_idx)} motor); {len(self._ann)} markers")

    def _windows_at(self, onsets: list[float]) -> np.ndarray:
        out = []
        for o in onsets:
            i0 = int(o * self.fs)
            if i0 + self.n_times <= self._data.shape[1]:
                out.append(self._data[:, i0:i0 + self.n_times])
        return np.stack(out) if out else np.empty((0, len(self.channel_names), self.n_times))

    def calibration_windows(self) -> tuple[np.ndarray, np.ndarray]:
        exec_on = [o for o, d in zip(self._ann.onset, self._ann.description)
                   if d == self._exec_label]
        rest_on = list(np.arange(self._rest_window[0], self._rest_window[1], config.WINDOW_SEC))
        return self._windows_at(exec_on), self._windows_at(rest_on)

    def _label_at(self, t: float) -> str:
        """The most recent marker within 3 s of time t (for the on-screen cue)."""
        recent = [d for o, d in zip(self._ann.onset, self._ann.description)
                  if 0 <= t - o <= 3.0 and "impedance" not in d]
        return recent[-1].split("/")[-1] if recent else "rest / baseline"

    def stream(self) -> Iterator[np.ndarray]:
        step = int(config.STEP_SEC * self.fs)
        while True:
            for i in range(self._start, self._data.shape[1] - self.n_times, step):
                self.recorded_condition = self._label_at(i / self.fs)
                yield self._data[:, i:i + self.n_times]


# --------------------------------------------------------------------------- #
def make_source(kind: str, subject: int = 1, **options):
    """Factory used by server.py: map a --source string to a Source instance."""
    if kind == "sim":
        return SimSource()
    if kind == "file":
        return FileSource(subject=subject)
    if kind == "live":
        return LiveSource(**options)
    if kind == "lsl":
        return LslSource(**options)
    if kind == "cnt":
        return CntSource(**options)
    raise ValueError(f"unknown source {kind!r} (use sim|file|live|lsl|cnt)")
