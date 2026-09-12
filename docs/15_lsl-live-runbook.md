# 15 — Live hardware runbook (eego 24 · BrainFlow · LSL)

How to get live EEG from the sponsor's amplifier into the model and the website. Written
for the confirmed hardware: **ANT Neuro eego 24 (EE‑511) with the NA‑246 cap**, a subset of
the eego 64 used to record the sample dataset.

## The one constraint that shapes everything

**BrainFlow's ANT Neuro backend runs on Windows/Linux only** — it cannot open the eego from
a Mac. So there are three ways to get the data, depending on which machine shows the demo.

| # | Path | Runs the demo on | Notes |
|---|---|---|---|
| A | eego → **BrainFlow** (`--source live`) | the **Windows** laptop | most direct; needs the board ID + channel rows |
| B | eego → BrainFlow **bridge** → **LSL** → `--source lsl` | your **Mac** | Windows runs the bridge; Mac consumes over the network |
| C | eego → ANT's **native LSL** output → `--source lsl` | your **Mac** | no BrainFlow; often most reliable (see below) |

All three feed the *same* pipeline — the `Source` seam means the model, server and website
don't change. Pick by where you want the browser to run.

### Why C can beat A/B
Only one process can own the amplifier at a time. If Michael's eego software is already
recording, BrainFlow may not be able to open the device. ANT's software can emit an LSL
stream itself — using that (path C) avoids fighting for the device. Ask the mentor whether
the eego software can output LSL; if yes, C is the simplest route to your Mac.

## Confirm the montage first (from the pinouts)

The eego 24 has fewer sites than the 64, so **check that our 12 channels are wired in the
NA‑246 cap**: `FC3 FC4 C3 C1 Cz C2 C4 CP3 CP4 Fz Pz Oz`. Get the pinout table from Michael.
- If all 12 are present → use them.
- If one or two aren't → just list the ones that are with `--lsl-channels` (LSL) or a shorter
  `--channel-rows`/labels (BrainFlow). The fidelity score adapts to any subset; only
  motor‑strip channels (see `config.MOTOR_SITES`) feed the score, the rest are context.

## Commands

**Path A — all on Windows (BrainFlow):**
```
python src/server.py --source live --board-id <EE511_ID> \
    --channel-rows <12 board rows from pinout> --calib-sec 30
# open http://127.0.0.1:8766 on that laptop
```
Confirm `<EE511_ID>` with the mentor — BrainFlow assigns a numeric board id per eego model,
and EE‑511 may differ from the EE‑410/411 ids.

**Path B — Windows bridges to your Mac (BrainFlow → LSL):**
```
# On the Windows laptop (plugged into the eego):
python scripts/06_brainflow_to_lsl.py --board-id <EE511_ID> \
    --channel-rows <rows> --labels FC3,FC4,C3,C1,Cz,C2,C4,CP3,CP4,Fz,Pz,Oz
# On your Mac (same network):
python src/server.py --source lsl --lsl-name rEEGainTest --calib-sec 30
```

**Path C — ANT native LSL → your Mac:**
```
# Windows: start the eego software's LSL output.
# Mac:
python src/server.py --source lsl --calib-sec 30      # picks the first EEG stream
```

**Unicorn fallback (if the g.tec is available), over LSL:**
```
python src/server.py --source lsl --montage unicorn --calib-sec 30
```
Unicorn is 8 channels; only C3/Cz/C4 are motor, so the score is weaker but the pitch — "we
tested across two amplifiers" — is stronger.

## Networking (paths B and C)

- Both laptops must be on the **same network**. LSL discovers streams via multicast.
- **Firewall**: allow Python through the macOS firewall, or discovery silently fails.
- **Most reliable link**: a direct Ethernet cable between the laptops. Your MacBook Air M4 is
  USB‑C only → bring a **USB‑C→Ethernet adapter** + cable. Backup: a phone **hotspot** both
  join. (You do NOT plug the EEG into the Mac — only the network.)
- If multicast is blocked, LSL can be pointed at a known peer IP via an `lsl_api.cfg`
  (`KnownPeers`) file; ask if the venue network misbehaves.

## Test the whole path with NO hardware (do this before build day)

```
# Terminal 1 — a synthetic LSL EEG outlet (12-lead eego layout):
python scripts/05_lsl_test.py --montage eego
# Terminal 2 — the real server consuming it:
python src/server.py --source lsl --lsl-name rEEGainTest --calib-sec 15
```
Or exercise the BrainFlow→LSL bridge itself with BrainFlow's synthetic board:
```
python scripts/06_brainflow_to_lsl.py --board-id -1 \
    --labels FC3,FC4,C3,C1,Cz,C2,C4,CP3,CP4,Fz,Pz,Oz
python src/server.py --source lsl --lsl-name rEEGainTest --calib-sec 15
```
Both were verified end-to-end on macOS (arm64).

## Offline fallback (if real-time fails)

Michael can record and export an **EDF** from the eego. That loads through the same offline
path as PhysioNet: point `data.py`/`FileSource` at the exported file, calibrate on its
movement vs rest segments, and replay it. Not live, but real subject data and a guaranteed demo.

## Build-day checklist

1. Get the pinout; confirm which of our 12 channels the NA‑246 wires.
2. Decide the path (A on Windows / B or C to the Mac) and pre-test it with the synthetic tools.
3. Confirm the EE‑511 BrainFlow board id (paths A/B) OR that eego can emit LSL (path C).
4. Same network + firewall allowed; bring the USB‑C→Ethernet adapter.
5. Calibrate on a volunteer (`--calib-sec 30`: 30 s attempt-to-move, 30 s rest).
6. Run the 5-condition demo; **record a backup video immediately**.
7. Keep `--source file` ready as the ultimate fallback.
