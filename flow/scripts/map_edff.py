#!/usr/bin/env python3
"""Map DFF + enable-MUX (MUX2 or MUXTG2) pairs in a synthesised netlist to the EDFF cell.

The TR10_cmp_sc ``EDFF`` macro is the source ``EDFFRB`` layout with the
active-low reset gate tied to VDD inside the cell (M2/V1/M1 strap).  It is a
pure enable DFF with no RSTB pin, so a netlist pair::

    MUX2  m (.A(data), .B(q), .S(en), .Y(d));
    DFF   r (.CK(ck), .D(d), .Q(q), .QB(qb));

can be replaced by one instance::

    EDFF  r (.CK(ck), .D(data), .E(en), .Q(q), .QB(qb));

This is an exact technology mapping (the mux feedback is the enable), not a
functional change.  The 1 remaining non-enable DFF and the non-FF MUX2 are
left alone.

Usage::

    python3 flow/scripts/map_edff.py <netlist.nl.v> [<output>]

Prints the number of replaced pairs.  The flow uses the output netlist for
the ODB build; run it after ``Yosys.Synthesis`` and resume from the next
step.
"""

from __future__ import annotations

import re
import sys

INST_RE = re.compile(r"(?ms)^  (DFF|MUX2|MUXTG2) (\S+) \(\n(.*?)\);\n")
PIN_RE = re.compile(r"\.(\w+)\s*\(\s*([^)]*?)\s*\)")


def normalize(net: str) -> str:
    return re.sub(r"\s+", "", net)


def parse(text: str):
    """Return {name: (cell, pins, span)} plus the raw matches."""
    out = {}
    for match in INST_RE.finditer(text):
        cell, name, body = match.group(1), match.group(2), match.group(3)
        pins = {pin: normalize(value) for pin, value in PIN_RE.findall(body)}
        out[name] = (cell, pins, match.span())
    return out


def main() -> int:
    if len(sys.argv) not in (2, 3):
        print(__doc__)
        return 2
    src = sys.argv[1]
    dst = sys.argv[2] if len(sys.argv) == 3 else src
    text = open(src, encoding="utf8").read()

    insts = parse(text)
    dffs = {name: (pins, span) for name, (cell, pins, span) in insts.items() if cell == "DFF"}
    muxes = {name: (pins, span) for name, (cell, pins, span) in insts.items() if cell in {"MUX2", "MUXTG2"}}

    # index the DFFs by their D and Q nets
    by_d = {pins.get("D"): (name, pins, span) for name, (pins, span) in dffs.items()}
    by_q = {pins.get("Q"): (name, pins, span) for name, (pins, span) in dffs.items()}

    replacements = []  # (span, new_text)
    removed = []
    for mux_name, (mux, mux_span) in muxes.items():
        y = mux.get("Y")
        b = mux.get("B")
        a = mux.get("A")
        s = mux.get("S")
        if not all((y, b, a, s)):
            continue
        hit = by_d.get(y)
        if hit is None:
            continue
        dff_name, dff, dff_span = hit
        q = dff.get("Q")
        if b == q:
            data, hold = a, b
        elif a == q:
            # counters put the hold value on A and the new value on B
            data, hold = b, a
        else:
            continue
        # a space before ')' terminates Verilog escaped identifiers such as
        # \mem0[0] (the original netlist has one too)
        new = (
            f"  EDFF {dff_name} (\n"
            f"    .CK({dff.get('CK', '')} ),\n"
            f"    .D({data} ),\n"
            f"    .E({s} ),\n"
            f"    .RSTB(edff_rstb_tie ),\n"
            f"    .Q({dff.get('Q', '')} ),\n"
            f"    .QB({dff.get('QB', '')} ));\n"
        )
        replacements.append((dff_span, new))
        removed.append((mux_span, ""))
        by_d.pop(y, None)  # do not reuse this DFF
        by_q.pop(b, None)

    for span, new in sorted(replacements + removed, key=lambda item: item[0][0], reverse=True):
        text = text[: span[0]] + new + text[span[1] :]

    if replacements:
        # one TIEHI drives every EDFF reset (RSTB is active low; tie it high)
        text = re.sub(
            r"(module \w+\s*\(.*?\);)",
            r"\1\n  wire edff_rstb_tie;",
            text,
            count=1,
            flags=re.S,
        )
        text = text.replace(
            "endmodule",
            "  TIEHI edff_tie (.HI(edff_rstb_tie));\nendmodule",
            1,
        )

    open(dst, "w", encoding="utf8").write(text)
    print(f"EDFF: replaced {len(replacements)} DFF+MUX pair(s) -> {dst}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
