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
then share one merged well.  This flow leaves via-access gaps between
cells, so the halos overlap by 1.8 um at the usual 10.8 um gap and the
wells still merge.  A gap of 16.2 or 21.6 um, however, leaves two separate
well islands with 3.6 / 9.0 um between them:

* ``WN.S1`` needs >= 4.0 um between separate wells,
* ``WN.S7`` needs >= 12.0 um between separate wells.

Both bands are illegal.  The only legal gaps are <= 12.6 um (merge) or
>= 24.6 um (12.0 + 2 x 6.3).  A normal N-well rectangle (layer 140/0) in
the gap merges the islands, exactly as abutting placement would.

Two cases are handled:

* **same row**: two instances of one row separated by a forbidden gap;
* **adjacent rows**: an N row and the FS row below it have wells that
  overlap vertically (the FS mirror puts its well in the lower half), so
  their *x* gap also has to be legal.  This is the ``N(row) -> FS(row+59.4)``
  overlap; the bridge is placed in the y-overlap of the two well bands.

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
ROW_H = 59.4
# N-well y band relative to the instance origin, by placement orientation.
WELL_Y = {
    "N": (29.6, 63.4),
    "R0": (29.6, 63.4),
    "FS": (-4.0, 29.8),
    "S": (-4.0, 29.8),
}


def parse_components(def_path: str, cell_info: dict) -> list[dict]:
    text = open(def_path, encoding="utf8").read()
    body = text.split("COMPONENTS")[1].split("END COMPONENTS")[0]
    out = []
    pattern = r"(?m)^\s*-\s+(\S+)\s+(\S+)\s+\+.*?\(\s*(-?\d+)\s+(-?\d+)\s*\)\s+(\w+)"
    for match in re.finditer(pattern, body):
        cell, x, y, orient = (
            match.group(2),
            int(match.group(3)) / 1000.0,
            int(match.group(4)) / 1000.0,
            match.group(5).upper(),
        )
        info = cell_info.get(cell)
        if info is None:
            continue
        out.append(
            {
                "cell": cell,
                "x0": x,
                "x1": x + info["width_um"],
                "y": y,
                "orient": orient if orient in WELL_Y else "N",
            }
        )
    return out


def well_band(inst: dict) -> tuple[float, float]:
    lo, hi = WELL_Y[inst["orient"]]
    return inst["y"] + lo, inst["y"] + hi


def main() -> int:
    gds = os.environ["WELLBRIDGE_GDS"]
    def_path = os.environ["WELLBRIDGE_DEF"]
    out = os.environ["WELLBRIDGE_OUT"]
    cell_info_path = os.environ.get(
        "WELLBRIDGE_CELL_INFO", "libs.ref/TR10_cmp_sc/src/cell_info.json"
    )

    cell_info = json.load(open(cell_info_path, encoding="utf8"))
    insts = parse_components(def_path, cell_info)

    layout = pya.Layout()
    layout.read(gds)
    wn = layout.layer(*WN_LAYER)
    top = layout.top_cell()

    lo, hi = 2 * WELL_HALO, 2 * WELL_HALO + WN_S7_MIN  # 12.6 .. 24.6
    bridges = []

    def add(x0: float, y0: float, x1: float, y1: float, why: str) -> None:
        if x1 - x0 <= 1e-9 or y1 - y0 <= 1e-9:
            return
        top.shapes(wn).insert(
            pya.Box(round(x0 * 1000), round(y0 * 1000), round(x1 * 1000), round(y1 * 1000))
        )
        bridges.append((why, x0, y0, x1, y1))

    # Same-row gaps.
    by_row: dict[float, list[dict]] = {}
    for inst in insts:
        by_row.setdefault(inst["y"], []).append(inst)
    for y, row in sorted(by_row.items()):
        row.sort(key=lambda i: i["x0"])
        for left, right in zip(row, row[1:]):
            gap = right["x0"] - left["x1"]
            if not (lo < gap < hi):
                continue
            wy0, wy1 = well_band(left)
            add(left["x1"], wy0, right["x0"], wy1, f"{left['cell']}->{right['cell']} row y={y:g} gap={gap:g}")

    # Vertical overlap with the FS row below (dy = +59.4).
    rows = sorted(by_row)
    for y in rows:
        below = y + ROW_H
        if below not in by_row:
            continue
        for up in by_row[y]:
            uy0, uy1 = well_band(up)
            for dn in by_row[below]:
                dy0, dy1 = well_band(dn)
                oy0, oy1 = max(uy0, dy0), min(uy1, dy1)
                if oy1 - oy0 <= 1e-9:
                    continue
                gap = dn["x0"] - up["x1"]
                if not (lo < gap < hi):
                    continue
                add(up["x1"], oy0, dn["x0"], oy1, f"{up['cell']}@y={y:g}->{dn['cell']}@y={below:g} gap={gap:g}")

    layout.write(out)
    for why, x0, y0, x1, y1 in bridges:
        print(f"well bridge: {why} -> ({x0:.1f},{y0:.1f})-({x1:.1f},{y1:.1f})")
    print(f"{len(bridges)} well bridge(s) -> {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
