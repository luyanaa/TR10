#!/usr/bin/env python3
"""PDK check entry point for the RX_TIA layout signoff.

Runs the KLayout DRC deck (must report zero violations), the KLayout LVS
deck against the strict netlist (must report TR10_LVS PASS) and the Magic
PEX flow, then prints the extracted node capacitances.

    python3 examples/rf_iq_receiver/checks/test_layout.py
"""
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
PKG = os.path.abspath(os.path.join(HERE, ".."))
SIGNOFF = os.path.join(PKG, "layout", "run_signoff.sh")


def main() -> int:
    proc = subprocess.run(["bash", SIGNOFF, os.path.join(PKG, "layout", "pex")],
                          capture_output=True, text=True, timeout=1200)
    out = proc.stdout + proc.stderr
    print(out)
    ok = ("DRC violations: 0" in out) and ("TR10_LVS PASS" in out) and proc.returncode == 0
    print("LAYOUT SIGNOFF:", "PASS" if ok else "FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
