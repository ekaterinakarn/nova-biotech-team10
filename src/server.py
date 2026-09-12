"""The realtime loop: pull a window -> score -> smooth -> emit a Frame over WebSocket,
~20x per second. Also serves the ui/ folder over HTTP so one command runs the whole demo.

This is where the loop CLOSES (requirement R4): the fidelity value decides the coaching
text and state in each Frame, which changes what the user is asked to do, which changes
their next window.

Usage:
    python src/server.py --source file --subject 1     # replay a real recording (Mac demo)
    python src/server.py --source sim                   # synthetic, no data needed
    python src/server.py --source live                  # ANT Neuro eego (Windows, Sept 12)

Then open the page it prints (http://127.0.0.1:8766) in a browser.
"""

from __future__ import annotations

import argparse
import asyncio
import functools
import http.server
import os
import tempfile
import threading
import time
from pathlib import Path

import sys

import numpy as np
import websockets

# Allow `python src/server.py` (run as a script) to import the `src` package.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src import config
from src.contracts import Frame
from src.fidelity import FidelityScorer
from src.sources import make_source
from src.quality import QualityGate

UI_DIR = Path(__file__).resolve().parents[1] / "ui"


def _state_and_coaching(fidelity: float) -> tuple[str, str]:
    """Map a fidelity value to a UI state label and the closed-loop coaching prompt."""
    if fidelity >= config.ENGAGED_THRESHOLD:
        return "engaged", "Continue imagining the sensation of gently closing your hand."
    if fidelity <= config.REST_THRESHOLD:
        return "rest", "Relax, then imagine gently closing your hand without moving."
    return "ambiguous", "Focus on the sensation of squeezing, not the picture."


class NeuroLoopServer:
    """Owns the source, the scorer, the connected clients, and the demo controls."""

    def __init__(self, source_kind: str, subject: int, sham: bool, **live_options) -> None:
        self.source = make_source(source_kind, subject=subject, **live_options)
        self.source_kind = source_kind
        self.quality = None
        # Live/LSL montages may have fewer channels than our 12-lead default; the source
        # tells the scorer which columns are motor channels (else the default MOTOR_IDX).
        self.scorer = FidelityScorer(
            channel_idx=getattr(self.source, "motor_idx", config.MOTOR_IDX))
        self.clients: set = set()
        self.sham = sham
        self.condition = ""            # set by the UI for the 5-condition demo
        self._activation = 0.0         # smoothed value (EMA), drives the hand
        self._templates: tuple[np.ndarray, np.ndarray] | None = None

    def calibrate(self) -> None:
        """Build the personal templates from the source's calibration windows."""
        X_exec, X_rest = self.source.calibration_windows()
        self.quality = QualityGate(np.concatenate([X_exec, X_rest]))
        X_exec = np.array([w for w in X_exec if self.quality.check(w)])
        X_rest = np.array([w for w in X_rest if self.quality.check(w)])
        if min(len(X_exec), len(X_rest)) < 5:
            raise ValueError("Too few clean calibration windows; repeat calibration")
        self.scorer.calibrate(X_exec, X_rest)
        # Keep the honest templates so we can toggle sham on/off live.
        self._templates = (self.scorer.C_exec.copy(), self.scorer.C_rest.copy())
        print(f"calibrated on {len(X_exec)} movement + {len(X_rest)} rest windows "
              f"@ {self.source.fs:.0f} Hz")

    async def handle_client(self, ws) -> None:
        """Register a browser, then listen for its control messages (sham/condition)."""
        self.clients.add(ws)
        try:
            async for message in ws:
                if message == "sham:on":
                    self.sham = True
                elif message == "sham:off":
                    self.sham = False
                elif message.startswith("condition:"):
                    self.condition = message.split(":", 1)[1]
        finally:
            self.clients.discard(ws)

    async def produce(self) -> None:
        """Score windows and broadcast Frames at STREAM_HZ."""
        period = 1.0 / config.STREAM_HZ
        interval = config.WINDOW_SEC if self.source_kind == "file" else config.STEP_SEC
        stream = self.source.stream()
        started = time.monotonic()
        while True:
            # Source acquisition may block; never block WebSocket controls/reconnects.
            window = await asyncio.to_thread(next, stream)
            valid = self.quality.check(window)
            if valid:
                d_exec, d_rest = self.scorer.distances(window)
                total = d_exec + d_rest
                fidelity = d_rest / total if total > 0 else 0.5
                state, coaching = _state_and_coaching(fidelity)
            else:
                fidelity, d_exec, d_rest = 0.5, 0.0, 0.0
                state, coaching = "rest", "Signal paused. Relax and check electrode contact."
            deadline = time.monotonic() + interval
            while time.monotonic() < deadline:
                # Re-evaluate the control immediately, even while holding a replay window.
                shown = 0.5 if self.sham else fidelity
                shown_state, shown_coaching = _state_and_coaching(shown) if valid else (state, coaching)
                self._activation = (config.SMOOTHING * self._activation
                                    + (1 - config.SMOOTHING) * (shown if valid else 0))
                frame = Frame(
                    t=round(time.monotonic() - started, 3), fidelity=round(shown, 3),
                    activation=round(self._activation, 3), state=shown_state,
                    condition=self.condition, signal_ok=valid, coaching=shown_coaching,
                    d_exec=round(d_exec, 3), d_rest=round(d_rest, 3),
                )
                if self.clients:
                    import json
                    payload = json.loads(frame.to_json())
                    payload.update(source=self.source_kind, sham=self.sham,
                                   recorded_condition=getattr(self.source, "recorded_condition", ""))
                    websockets.broadcast(self.clients, json.dumps(payload))
                await asyncio.sleep(period)

    async def run(self) -> None:
        await asyncio.to_thread(self.calibrate)
        async with websockets.serve(self.handle_client, config.WS_HOST, config.WS_PORT):
            print(f"WebSocket streaming on ws://{config.WS_HOST}:{config.WS_PORT}")
            await self.produce()


class DemoUIHandler(http.server.SimpleHTTPRequestHandler):
    """Development assets must be reloaded after UI changes, including ES modules."""

    def end_headers(self):
        self.send_header("Cache-Control", "no-store")
        super().end_headers()


def serve_ui(port: int) -> None:
    """Serve the ui/ folder over HTTP in a background thread (stdlib only)."""
    handler = functools.partial(DemoUIHandler, directory=str(UI_DIR))
    httpd = http.server.ThreadingHTTPServer((config.WS_HOST, port), handler)
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    print(f"UI available at http://{config.WS_HOST}:{port}")


def main() -> None:
    ap = argparse.ArgumentParser(description="NeuroLoop realtime server")
    ap.add_argument("--source", choices=["sim", "file", "live", "lsl", "cnt"], default="file")
    ap.add_argument("--cnt-file", help="path to a recorded ANT eego .cnt session (--source cnt)")
    ap.add_argument("--subject", type=int, default=4, help="PhysioNet subject for --source file")
    ap.add_argument("--sham", action="store_true", help="start with the model broken (chance)")
    ap.add_argument("--ui-port", type=int, default=config.WS_PORT + 1)
    # --source live (BrainFlow, Windows/Linux)
    ap.add_argument("--board-id", type=int, help="Mentor-confirmed BrainFlow board ID")
    ap.add_argument("--channel-rows", help="12 comma-separated BrainFlow rows in config.CHANNELS order")
    ap.add_argument("--serial-port", default="")
    # --source lsl (Lab Streaming Layer, cross-platform incl. macOS)
    ap.add_argument("--montage", choices=list(config.MONTAGES), default="eego",
                    help="channel layout to pull from the LSL stream")
    ap.add_argument("--lsl-name", help="exact LSL stream name (else the first EEG stream)")
    ap.add_argument("--lsl-channels", help="comma-separated channel labels, overrides --montage "
                                           "(e.g. for an eego 24 subset)")
    ap.add_argument("--lsl-peer", help="IP of the machine running the LSL outlet; sets up a "
                                       "direct link when Wi-Fi/hotspot blocks LSL discovery")
    ap.add_argument("--calib-sec", type=float, help="seconds per calibration block (live/lsl)")
    args = ap.parse_args()
    live_options = {}
    if args.source == "live":
        if args.board_id is None or args.channel_rows is None:
            ap.error("live requires --board-id and --channel-rows verified with the mentor")
        try:
            rows = [int(row) for row in args.channel_rows.split(",")]
        except ValueError:
            ap.error("channel rows must be comma-separated integers")
        live_options = dict(board_id=args.board_id, channel_rows=rows, serial_port=args.serial_port)
    elif args.source == "lsl":
        channels = ([c.strip() for c in args.lsl_channels.split(",")]
                    if args.lsl_channels else None)
        live_options = dict(montage=args.montage, channels=channels, stream_name=args.lsl_name)
    elif args.source == "cnt":
        if not args.cnt_file:
            ap.error("cnt requires --cnt-file <path to .cnt recording>")
        live_options = dict(cnt_file=args.cnt_file)
    if args.calib_sec is not None and args.source in ("live", "lsl"):
        live_options["exec_sec"] = args.calib_sec
        live_options["rest_sec"] = args.calib_sec

    # A direct LSL link for when discovery multicast is blocked (venue Wi-Fi / hotspot).
    # Must be set before pylsl loads liblsl, i.e. before the source is created below.
    if args.lsl_peer:
        cfg = os.path.join(tempfile.gettempdir(), "neuroloop_lsl_api.cfg")
        with open(cfg, "w") as fh:
            fh.write(f"[lab]\nKnownPeers = {{{args.lsl_peer}}}\n")
        os.environ["LSLAPICFG"] = cfg
        print(f"LSL direct link -> {args.lsl_peer}")

    serve_ui(args.ui_port)
    server = NeuroLoopServer(args.source, args.subject, args.sham, **live_options)
    try:
        asyncio.run(server.run())
    except KeyboardInterrupt:
        print("\nstopped")
    finally:
        close = getattr(server.source, "close", None)
        if close:
            close()


if __name__ == "__main__":
    main()
