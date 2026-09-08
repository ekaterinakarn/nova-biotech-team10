"""Tests for the wire contract: a Frame must survive a JSON round-trip unchanged, so the
browser reads exactly what the server sent."""

from __future__ import annotations

from src.contracts import Frame


def test_frame_json_round_trip():
    f = Frame(
        t=1.5, fidelity=0.83, activation=0.71, state="engaged",
        condition="imagine", signal_ok=True, coaching="feel the tension",
        d_exec=0.4, d_rest=0.9,
    )
    assert Frame.from_json(f.to_json()) == f


def test_frame_defaults():
    """Only the three numbers are required; the rest have sensible defaults."""
    f = Frame(t=0.0, fidelity=0.5, activation=0.5)
    assert f.state == "rest" and f.signal_ok is True and f.coaching == ""
