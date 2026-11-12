#!/usr/bin/env python3
"""Add N-well bridges in the cell-row gaps that would otherwise fail WN.S1/S7.

Run with KLayout's Python (KLayout does not forward ``--`` arguments, so
the paths come from the environment)::

    WELLBRIDGE_GDS=runs/<tag>/46-klayout-streamout/<top>.gds \
    WELLBRIDGE_DEF=runs/<tag>/33-openroad-detailedplacement/<top>.def \
    WELLBRIDGE_OUT=/tmp/<top>.wellbridge.gds \
    WELLBRIDGE_CELL_INFO=libs.ref/TR10_cmp_sc/src/cell_info.json \
        klayout -b -r flow/scripts/add_well_bridges.py

Why this is needed
------------------
The TR10_cmp_sc cells draw their N-well with a 6.3 um halo on each side
because the library is laid out for *abutting* placement: two neighbours
then share one merged well.  This flow deliberately leaves a 10.8 um
via-access gap between cells, so the halos overlap by 1.8 um and the wells
still merge.  A gap of 16.2 or 21.6 um, however, leaves the two wells as
separate islands with 3.6 / 9.0 um between them:

* ``WN.S1`` needs >= 4.0 um between separate wells,
* ``WN.S7`` needs >= 12.0 um between separate wells.

Both bands are illegal.  The only legal gaps are <= 12.6 um (merge) or
>= 24.6 um (12.0 + 2 x 6.3).  The placement occasionally lands a cell 16.2
or 21.6 um before a fixed TAP, and the KLayout sign-off DRC then reports
``WN.S1``/``WN.S7``/``WN.AN`` at that edge.

Bridging the gap with a normal N-well rectangle (layer 140/0) merges the
two islands, which is what abutting placement would have done.  The bridge
spans the well y-band of the row (y + 29.6 .. y + 63.4) and reaches the two
cells' halos, so the resulting region is one polygon.

The script is a post-streamout step: the KLayout DRC deck reads the GDS,
so the bridge has to exist in the GDS.  It does not touch metal, diffusion
or connectivity; LVS is unaffected.
"""

from __future__ import annotations

import json
import os
import re

import pya

WN_LAYER = (140, 0)
WELL_HALO = 6.3  # um, from the cell GDS
WN_S7_MIN = 12.0  # um, run.drc
WELL_Y0, WELL_Y1 = 29.6, 63.4  # relative to the row origin


def parse_components(def_path: str, cell_info: dict) -> dict[float, list[tuple[float, float, str]]]:
    text = open(def_path, encoding="utf8").read()
    body = text.split("COMPONENTS")[1].split("END COMPONENTS")[0]
    rows: dict[float, list[tuple[float, float, str]]] = {}
    for match in re.finditer(
        r"(?m)^\s*-\s+(\S+)\s+(\S+)\s+\+.*?\(\s*(-?\d+)\s+(-?\d+)\s*\)", body
    ):
        cell, x, y = match.group(2), int(match.group(3)) / 1000.0, int(match.group(4)) / 1000.0
        info = cell_info.get(cell)
        if info is None:
            continue
        rows.setdefault(y, []).append((x, x + info["width_um"], cell))
    return rows


def main() -> int:
    gds = os.environ["WELLBRIDGE_GDS"]
    def_path = os.environ["WELLBRIDGE_DEF"]
    out = os.environ["WELLBRIDGE_OUT"]
    cell_info_path = os.environ.get("WELLBRIDGE_CELL_INFO", "libs.ref/TR10_cmp_sc/src/cell_info.json")

    cell_info = json.load(open(cell_info_path, encoding="utf8"))
    rows = parse_components(def_path, cell_info)

    layout = pya.Layout()
    layout.read(gds)
    wn = layout.layer(*WN_LAYER)
    top = layout.top_cell()

    lo, hi = 2 * WELL_HALO, 2 * WELL_HALO + WN_S7_MIN  # 12.6 .. 24.6
    added = 0
    for y, cells in sorted(rows.items()):
        cells.sort()
        for (_, left_end, left_cell), (right_start, _, right_cell) in zip(cells, cells[1:]):
            gap = right_start - left_end
            if not (lo < gap < hi):
                continue
            box = pya.Box(
                round(left_end * 1000),
                round((y + WELL_Y0) * 1000),
                round(right_start * 1000),
                round((y + WELL_Y1) * 1000),
            )
            top.shapes(wn).insert(box)
            print(f"well bridge: {left_cell}->{right_cell} row y={y:g} gap={gap:g}um")
            added += 1

    layout.write(out)
    print(f"{added} well bridge(s) -> {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
