"""Regression checks for rejected signals, source pacing and live filtering."""
import asyncio
import json
import numpy as np
from src import config
from src.quality import QualityGate
from src.sources import SimSource, LiveSource
from src.server import NeuroLoopServer


def test_quality_rejects_flat_nonfinite_and_large_artifacts():
    source = SimSource()
    movement, rest = source.calibration_windows()
    gate = QualityGate(np.concatenate([movement, rest]))
    clean = next(source.stream())
    assert gate.check(clean)
    for bad in [np.zeros_like(clean), clean * 100, clean[:, :1]]:
        assert not gate.check(bad)
    bad = clean.copy(); bad[0, 0] = np.nan
    assert not gate.check(bad)
    bad = clean.copy(); bad[3] = 0
    assert not gate.check(bad)


def test_live_filter_keeps_motor_band_and_suppresses_drift():
    source = LiveSource.__new__(LiveSource)
    source.fs = 160
    t = np.arange(320) / source.fs
    x = np.tile(np.sin(2*np.pi*12*t) + 5*np.sin(2*np.pi*2*t), (12, 1))
    filtered = source._filter(x)
    interior = slice(60, -60)
    assert np.std(filtered[:, interior]) < np.std(x[:, interior]) / 2
    assert np.std(filtered[:, interior]) > 0.4
    assert filtered.shape == x.shape


def test_server_emits_quality_gate_and_remains_responsive(monkeypatch):
    async def scenario():
        server = NeuroLoopServer('sim', 4, False)
        server.calibrate()
        server.source.stream = lambda: iter([np.zeros((12, 320))] * 20)
        server.clients.add(object())
        frames = []
        monkeypatch.setattr('src.server.websockets.broadcast', lambda clients, message: frames.append(json.loads(message)))
        task = asyncio.create_task(server.produce())
        await asyncio.sleep(.16)
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass
        assert len(frames) >= 2
        assert all(not f['signal_ok'] and f['activation'] == 0 for f in frames)
        assert frames[-1]['t'] > frames[0]['t']
    asyncio.run(scenario())


def test_file_windows_are_held_for_window_duration(monkeypatch):
    async def scenario():
        server = NeuroLoopServer('sim', 4, False)
        server.calibrate()
        server.source_kind = 'file'
        calls = []
        source_stream = server.source.stream()
        def stream():
            while True:
                calls.append(1)
                yield next(source_stream)
        server.source.stream = stream
        task = asyncio.create_task(server.produce())
        await asyncio.sleep(.16)
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass
        assert len(calls) == 1
    asyncio.run(scenario())
