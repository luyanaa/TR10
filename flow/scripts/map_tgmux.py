#!/usr/bin/env python3
"""Replace remaining MUX2 instances with the 6T MUXTG2 macro.

``MUXTG2`` has the same pins as ``MUX2`` (A, B, Y, S, VDD, GND) but is the
compact 6T transmission-gate implementation, so the rewrite is a cell-name
substitution.  Run it after ``map_edff.py`` (which consumes DFF+MUX2 pairs)
and after ``map_dff2.py``.

Usage::

    python3 flow/scripts/map_tgmux.py <netlist.nl.v> [<output>]
"""

from __future__ import annotations

import re
import sys

INST_RE = re.compile(r"(?m)^(\s*)MUX2(\s+\S+\s*\()")


def main() -> int:
    if len(sys.argv) not in (2, 3):
        print(__doc__)
        return 2
    src = sys.argv[1]
    dst = sys.argv[2] if len(sys.argv) == 3 else src
    text = open(src, encoding="utf8").read()
    text, count = INST_RE.subn(r"\1MUXTG2\2", text)
    open(dst, "w", encoding="utf8").write(text)
    print(f"MUXTG2: replaced {count} MUX2 instance(s) -> {dst}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
