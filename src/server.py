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
import threading
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

UI_DIR = Path(__file__).resolve().parents[1] / "ui"


def _state_and_coaching(fidelity: float) -> tuple[str, str]:
    """Map a fidelity value to a UI state label and the closed-loop coaching prompt."""
    if fidelity >= config.ENGAGED_THRESHOLD:
        return "engaged", "Great — keep feeling the tension."
    if fidelity <= config.REST_THRESHOLD:
        return "rest", "Stop picturing it. Feel the tension in your forearm."
    return "ambiguous", "Focus on the sensation of squeezing, not the picture."


class NeuroLoopServer:
    """Owns the source, the scorer, the connected clients, and the demo controls."""

    def __init__(self, source_kind: str, subject: int, sham: bool) -> None:
        self.source = make_source(source_kind, subject=subject)
        self.scorer = FidelityScorer()
        self.clients: set = set()
        self.sham = sham
        self.condition = ""            # set by the UI for the 5-condition demo
        self._activation = 0.0         # smoothed value (EMA), drives the hand
        self._templates: tuple[np.ndarray, np.ndarray] | None = None

    def calibrate(self) -> None:
        """Build the personal templates from the source's calibration windows."""
        X_exec, X_rest = self.source.calibration_windows()
        self.scorer.calibrate(X_exec, X_rest)
        # Keep the honest templates so we can toggle sham on/off live.
        self._templates = (self.scorer.C_exec.copy(), self.scorer.C_rest.copy())
        self._apply_sham()
        print(f"calibrated on {len(X_exec)} movement + {len(X_rest)} rest windows "
              f"@ {self.source.fs:.0f} Hz")

    def _apply_sham(self) -> None:
        """Sham = make both templates identical, so fidelity collapses to ~0.5 (chance).
        This is the 'break it on purpose' demo and the sham arm of a future trial."""
        exec_t, rest_t = self._templates
        if self.sham:
            self.scorer.C_exec = rest_t.copy()   # identical templates -> d_exec ~ d_rest
            self.scorer.C_rest = rest_t.copy()
        else:
            self.scorer.C_exec, self.scorer.C_rest = exec_t.copy(), rest_t.copy()

    async def handle_client(self, ws) -> None:
        """Register a browser, then listen for its control messages (sham/condition)."""
        self.clients.add(ws)
        try:
            async for message in ws:
                if message == "sham:on":
                    self.sham = True; self._apply_sham()
                elif message == "sham:off":
                    self.sham = False; self._apply_sham()
                elif message.startswith("condition:"):
                    self.condition = message.split(":", 1)[1]
        finally:
            self.clients.discard(ws)

    async def produce(self) -> None:
        """Score windows and broadcast Frames at STREAM_HZ."""
        period = 1.0 / config.STREAM_HZ
        t = 0.0
        for window in self.source.stream():
            fidelity = self.scorer.score(window)
            d_exec, d_rest = self.scorer.distances(window)
            # Exponential moving average -> a fluid hand (docs/02).
            self._activation = (config.SMOOTHING * self._activation
                                + (1 - config.SMOOTHING) * fidelity)
            state, coaching = _state_and_coaching(fidelity)
            frame = Frame(
                t=round(t, 3), fidelity=round(fidelity, 3),
                activation=round(self._activation, 3), state=state,
                condition=self.condition, signal_ok=True, coaching=coaching,
                d_exec=round(d_exec, 3), d_rest=round(d_rest, 3),
            )
            if self.clients:
                websockets.broadcast(self.clients, frame.to_json())
            t += period
            await asyncio.sleep(period)

    async def run(self) -> None:
        self.calibrate()
        async with websockets.serve(self.handle_client, config.WS_HOST, config.WS_PORT):
            print(f"WebSocket streaming on ws://{config.WS_HOST}:{config.WS_PORT}")
            await self.produce()


def serve_ui(port: int) -> None:
    """Serve the ui/ folder over HTTP in a background thread (stdlib only)."""
    handler = functools.partial(http.server.SimpleHTTPRequestHandler, directory=str(UI_DIR))
    httpd = http.server.ThreadingHTTPServer((config.WS_HOST, port), handler)
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    print(f"UI available at http://{config.WS_HOST}:{port}")


def main() -> None:
    ap = argparse.ArgumentParser(description="NeuroLoop realtime server")
    ap.add_argument("--source", choices=["sim", "file", "live"], default="file")
    ap.add_argument("--subject", type=int, default=1, help="PhysioNet subject for --source file")
    ap.add_argument("--sham", action="store_true", help="start with the model broken (chance)")
    ap.add_argument("--ui-port", type=int, default=config.WS_PORT + 1)
    args = ap.parse_args()

    serve_ui(args.ui_port)
    server = NeuroLoopServer(args.source, args.subject, args.sham)
    try:
        asyncio.run(server.run())
    except KeyboardInterrupt:
        print("\nstopped")


if __name__ == "__main__":
    main()
