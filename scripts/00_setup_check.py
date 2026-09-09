"""Environment sanity check — run this FIRST, this week, not on build day.

What it does:
    Imports every dependency NeuroLoop needs and prints its version, so we discover
    install problems on our own laptops (esp. Python 3.13 on Apple Silicon) well before
    Sept 12. It also reports whether the live-amplifier backend (BrainFlow) can actually
    STREAM on this machine — which it cannot on macOS.

Why it matters:
    The single worst failure mode at a hackathon is "it doesn't install" discovered at
    9am on build day. This script verifies it in advance instead.

Usage:
    python scripts/00_setup_check.py
"""

from __future__ import annotations

import importlib
import platform
import sys

# (import name, pip name) — differ for scikit-learn.
REQUIRED = [
    ("numpy", "numpy"),
    ("scipy", "scipy"),
    ("sklearn", "scikit-learn"),
    ("mne", "mne"),
    ("pyriemann", "pyriemann"),
    ("matplotlib", "matplotlib"),
    ("websockets", "websockets"),
]

# brainflow is optional at IMPORT time everywhere, and only STREAMS on Windows/Linux.
OPTIONAL = [("brainflow", "brainflow")]


def _check(mod_name: str, pip_name: str) -> bool:
    """Import one module, print its version, return True on success."""
    try:
        mod = importlib.import_module(mod_name)
        version = getattr(mod, "__version__", "unknown")
        print(f"  ok    {pip_name:<14} {version}")
        return True
    except Exception as exc:  # noqa: BLE001 - we want to report any import failure
        print(f"  FAIL  {pip_name:<14} {exc}")
        return False


def main() -> int:
    print("NeuroLoop setup check")
    print(f"  Python {platform.python_version()} on {platform.system()} "
          f"({platform.machine()})")
    print()

    print("Required packages:")
    all_ok = all([_check(m, p) for m, p in REQUIRED])

    print("\nOptional (live amplifier):")
    for mod_name, pip_name in OPTIONAL:
        _check(mod_name, pip_name)

    # The live path needs the ANT Neuro backend, which BrainFlow only ships for
    # Windows/Linux. We can develop the whole system on macOS against SimSource/FileSource.
    if platform.system() == "Darwin":
        print("\n  note  macOS detected — brainflow imports but the ANT Neuro (eego)")
        print("        backend does not stream here. Use --source file/sim on this laptop;")
        print("        run --source live on the Windows machine on Sept 12.")

    print()
    if all_ok:
        print("All required packages import cleanly. You're ready to build.")
        return 0
    print("Some required packages failed. Fix with: pip install -r requirements.txt")
    return 1


if __name__ == "__main__":
    sys.exit(main())
