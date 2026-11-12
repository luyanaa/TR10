#!/usr/bin/env python3
"""Pair DFFs that share a clock into the DFF2 cell.

``DFF2`` is two DFF layouts side by side with their CK pins joined by an M2
strap in the CK band; it exposes one CK pin and D0/Q0/QB0 + D1/Q1/QB1.  This
is a pure pairing (same flops, one shared clock pin), so it halves the clock
pin count without changing function or area.

Usage::

    python3 flow/scripts/map_dff2.py <netlist.nl.v> [<output>]

Run it after ``map_edff.py`` (or on any netlist with plain DFFs); an odd DFF
is left as a DFF.
"""

from __future__ import annotations

import re
import sys

INST_RE = re.compile(r"(?ms)^  (DFF|MUX2|EDFF) (\S+) \(\n(.*?)\);\n")
PIN_RE = re.compile(r"\.(\w+)\s*\(\s*([^)]*?)\s*\)")


def norm(net: str) -> str:
    return re.sub(r"\s+", "", net)


def main() -> int:
    if len(sys.argv) not in (2, 3):
        print(__doc__)
        return 2
    src = sys.argv[1]
    dst = sys.argv[2] if len(sys.argv) == 3 else src
    text = open(src, encoding="utf8").read()

    dffs = []
    for m in INST_RE.finditer(text):
        if m.group(1) != "DFF":
            continue
        pins = {p: norm(v) for p, v in PIN_RE.findall(m.group(3))}
        dffs.append((m.group(2), pins, m.span()))

    by_ck: dict[str, list] = {}
    for dff in dffs:
        by_ck.setdefault(dff[1].get("CK", ""), []).append(dff)

    replacements = []
    removed = []
    n = 0
    for ck, group in by_ck.items():
        for i in range(0, len(group) - 1, 2):
            a_name, a, a_span = group[i]
            b_name, b, b_span = group[i + 1]
            name = f"dff2_{n}"
            n += 1
            new = (
                f"  DFF2 {name} (\n"
                f"    .CK({a.get('CK', '')} ),\n"
                f"    .D0({a.get('D', '')} ),\n"
                f"    .Q0({a.get('Q', '')} ),\n"
                f"    .QB0({a.get('QB', '')} ),\n"
                f"    .D1({b.get('D', '')} ),\n"
                f"    .Q1({b.get('Q', '')} ),\n"
                f"    .QB1({b.get('QB', '')} ));\n"
            )
            replacements.append((a_span, new))
            removed.append((b_span, ""))

    for span, new in sorted(replacements + removed, key=lambda x: x[0][0], reverse=True):
        text = text[: span[0]] + new + text[span[1] :]

    open(dst, "w", encoding="utf8").write(text)
    print(f"DFF2: paired {n * 2} DFF(s) into {n} DFF2 -> {dst}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
