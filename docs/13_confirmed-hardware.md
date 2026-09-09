# Hardware clarification — manuals supplied September 8

Emma uses an Apple Silicon Mac. The stated ANT system is eego mylab 64 + waveguard original.
The supplied datasheet identifies CA-208, a 64-channel 10/10 shielded cap, CPz reference and
AFz ground. The software challenge can still use a selected set of 12 channels; verify the
actual acquisition configuration with the technician.

## What the supplied documents establish

- `UDO-SM-0215rev09 CA-208 Datasheet 2020-12-14.pdf`, pages 2–4: cap layout, connector
  assignment, electrode channel numbers, and compatibility with EE-2xx amplifiers.
- `UDO-SM-0120_ENrev11 eego amplifier EE-22x User Manual 2025-07-01_02.pdf`, Appendix C:
  supplied version-3 specification lists Windows 11 64-bit, 8 GB RAM, USB 3.0 Type C.
  The technician must confirm the actual amplifier model/version; a family manual alone
  does not identify the specific physical device or authorize an alternative driver setup.
- Use the supplied USB cable and technician-supervised setup. Installing Python alone
  does not install/validate the amplifier's acquisition driver.

## Recommended connection to Emma's Mac

Cap → compatible amplifier → organizer's configured Windows acquisition PC → LSL stream
on a permitted local network → Python on Emma's Mac → local browser hand.

The manufacturer's eego software supports LSL export. LSL transports timestamped samples;
it does not replace the amplifier's driver. Sharing a room/Wi-Fi does not guarantee discovery:
confirm the network allows communication between the two computers. No cloud deployment
is necessary. If a network bridge is unavailable, run our model and UI on the acquisition PC.

The repo presently implements BrainFlow direct acquisition, synthetic input and recorded
input. An LSL input adapter and its simulated-stream tests still need implementation.
Do not describe the Mac bridge as already tested or available in the current CLI.

## Selecting the 12 electrodes

These are **cap channel numbers from the datasheet**, NOT BrainFlow matrix row numbers or
zero-based LSL indexes. Match stream labels first; check any manual mapping with the tech.

| Electrode | CA-208 cap channel |
|---|---:|
| FC3 | 41 |
| FC4 | 43 |
| C3 | 15 |
| C1 | 45 |
| Cz | 16 |
| C2 | 46 |
| C4 | 17 |
| CP3 | 48 |
| CP4 | 49 |
| Fz | 6 |
| Pz | 26 |
| Oz | 64 |

All our requested sites appear in the cap specification. If only 12 channels are streamed,
confirm that those sites are selected rather than blindly taking the first 12 channels.
CPz reference and AFz ground are not additional model features.

## g.tec practice equipment

The g.GAMMAcap is a cap platform compatible with multiple amplifiers, including g.HIamp,
g.USBamp and g.Nautilus. Its name does not identify the amplifier, driver, or available streaming
software. g.tec advertises LSL interfaces in its software ecosystem; confirm the actual supplied
amplifier/software package and whether LSL export will be enabled. BrainFlow's support for a
g.tec Unicorn does not imply support for every g.tec amplifier.

For switching devices: select an explicit stream, validate labels/order, units, sampling rate
and reference, reset buffers and quality thresholds, and recalibrate. A new device or participant
must not inherit the previous device/person's covariance templates. The model API and hand
renderer can remain unchanged while the acquisition adapter changes.

## Message for organizers (draft; not sent)

“We develop on an Apple Silicon Mac. Will the ANT and g.tec stations include Windows
computers with working drivers/software, and can both export live EEG through LSL to our
laptop? Which exact g.tec amplifier/software will be provided? Can we select our 12 electrode
sites, and will the local network permit streaming between the acquisition PC and our Mac?”

## Sources

- Supplied local cap and amplifier manuals listed above.
- https://academy.ant-neuro.com/faq (eego LSL and SDK support)
- https://www.gtec.at/product/ggammacap-research-eeg-cap/ (cap/amplifier compatibility)
- https://www.gtec.at/product/gtec-suite-2024-software/ (software/LSL interfaces)
- https://brainflow.readthedocs.io/en/stable/SupportedBoards.html (device-specific support)
