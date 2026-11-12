#!/usr/bin/env python3
"""Build the FEEDTHRU flow-level LVS harness GDS.

The library FEEDTHRU is a device-less cell, so the KLayout extractor emits no
top cell for it.  This script places one INV_X1 and one FEEDTHRU in a small
top cell (``FEEDTHRU_TEST``), wires the inverter output to the feedthrough
A strap, and adds top-level pin labels.  The extractor then has a real top
cell and the LVS contract can check the FEEDTHRU ports.

Run with KLayout's batch Python::

    klayout -b -r flow/scripts/build_feedthru_test.py \
        -rd lib_path=$PWD/libs.ref/TR10_cmp_sc/gds/TR10_cmp_sc.gds \
        -rd out_path=/tmp/feedthru_lvs/final/gds/FEEDTHRU_TEST.gds

Then::

    cp flow/checks/feedthru_test/FEEDTHRU_TEST.pnl.v /tmp/feedthru_lvs/final/pnl/
    bash flow/checks/test_klayout_lvs.sh /tmp/feedthru_lvs FEEDTHRU_TEST TR10_cmp_sc
"""

from __future__ import annotations

import pya


def main() -> int:
    layout = pya.Layout()
    layout.read(lib_path)
    inv = layout.cell("INV_X1")
    feed = layout.cell("FEEDTHRU")
    top = layout.create_cell("FEEDTHRU_TEST")
    top.insert(pya.CellInstArray(inv.cell_index(), pya.Trans(0, 0)))
    top.insert(pya.CellInstArray(feed.cell_index(), pya.Trans(10800, 0)))

    m1 = layout.layer(13, 0)
    m2 = layout.layer(20, 0)
    l1 = layout.layer(48, 0)
    l2 = layout.layer(49, 0)
    bd = layout.layer(235, 0)

    # INV_X1.Y (M2 6.4..9.8) -> FEEDTHRU.A (M2 11.8..15.2).
    top.shapes(m2).insert(pya.Box(6400, 27900, 15200, 31300))
    # Top-level pin patches: A on the inverter input, Y on the feedthrough
    # A strap; VDD/GND/VSS on the shared M1 rails.
    top.shapes(m2).insert(pya.Box(1000, 27900, 4400, 31300))
    top.shapes(m2).insert(pya.Box(11800, 27900, 15200, 31300))
    top.shapes(m1).insert(pya.Box(0, 55700, 16200, 58300))
    top.shapes(m1).insert(pya.Box(0, 1100, 16200, 3700))
    for text, x, y in (("A", 2700, 29600), ("Y", 13500, 29600)):
        top.shapes(l2).insert(pya.Text(text, pya.Trans(pya.Vector(x, y))))
    for text, x, y in (
        ("VDD", 2700, 57100),
        ("GND", 2700, 2400),
        ("VSS", 5000, 2400),
    ):
        top.shapes(l1).insert(pya.Text(text, pya.Trans(pya.Vector(x, y))))
    top.shapes(bd).insert(pya.Box(0, 0, 16200, 59400))

    layout.write(out_path)
    print(f"wrote {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
