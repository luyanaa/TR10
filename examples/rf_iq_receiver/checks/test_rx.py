#!/usr/bin/env python3
"""PDK check entry point for the RF I/Q receiver example.

Thin wrapper so a release gate can call
    python3 examples/rf_iq_receiver/checks/test_rx.py
and get the same PASS/FAIL verdict as scripts/run_cases.py.

Add --full to include the 1 MHz end-to-end AM transient (~5 min).
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.abspath(os.path.join(HERE, "..", "scripts")))

from run_cases import main  # noqa: E402

if __name__ == "__main__":
    sys.exit(main())
