"""Verify a running local demo server: HTTP, finite frames, control and restore.
Run after starting src/server.py. Temporarily changes the shared control mode.
"""
import asyncio
import json
import urllib.request
import websockets

async def main():
    async with websockets.connect('ws://127.0.0.1:8765') as ws:
        first = json.loads(await ws.recv())
        assert 0 <= first['fidelity'] <= 1
        original = first.get('sham', False)
        try:
            await ws.send('sham:on')
            for _ in range(20):
                frame = json.loads(await asyncio.wait_for(ws.recv(), 3))
                if frame['sham']:
                    assert frame['fidelity'] == .5
                    break
            else:
                raise AssertionError('Control did not apply')
        finally:
            await ws.send('sham:on' if original else 'sham:off')
    assert urllib.request.urlopen('http://127.0.0.1:8766', timeout=3).status == 200
    print('HTTP, WebSocket frames and identical-template control verified.')

if __name__ == '__main__':
    asyncio.run(main())
