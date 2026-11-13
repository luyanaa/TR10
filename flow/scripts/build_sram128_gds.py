#!/usr/bin/env python3
"""Normalise the upstream SRAM128 GDS into TR10 macro coordinates.

The pinned upstream view (``libs.ref/TR10_SRAM128/src/SRAM128.gds``) is a
standalone chip fragment: its geometry starts at ``(-82.1, -90.1)`` um and the
LEF says ``FOREIGN SRAM128 82.100 90.100`` so that a def2gds script can place
the cell at ``origin + (82.1, 90.1)``.

LibreLane merges the macro GDS into the design layout by cell name only -- it
does not apply the LEF FOREIGN offset -- so the raw view would put the SRAM
geometry 82.1/90.1 um away from its pins, rails and obstructions.  This script
therefore translates every shape of the top cell by ``(+82.1, +90.1)`` um so
the bounding box becomes ``(0, 0) - (1166.1, 185.6)`` (== the LEF SIZE) and
renames the ``VSS`` pin labels to ``GND`` (the TR10 ground net).

Nothing else about the view is touched: the layer numbers, the ``235/0``
outlines and the ``AREF`` arrays are kept exactly as published, so the derived
GDS and the pinned source differ only in the translation, the label text and
the GDS timestamps.

The sibling ``build_sram128_views.py`` drops the ``FOREIGN`` statement from
the LEF, so the LEF and GDS origins agree.

Usage::

    klayout -b -r flow/scripts/build_sram128_gds.py -rd src=... -rd out=...

If the shift is already applied the script is a no-op apart from the label
rename.
"""

from __future__ import annotations

import sys

import klayout.db as db

SHIFT_X_UM = 82.1
SHIFT_Y_UM = 90.1
TOP = "SRAM128"
LABEL_RENAME = {"VSS": "GND"}

# Pin label layers of the upstream view (METAL1/METAL2 text).
TEXT_LAYERS = {(48, 0), (49, 0)}


def main() -> int:
    src = globals().get("src")
    out = globals().get("out")
    if not src or not out:
        print("usage: -rd src=<gds> -rd out=<gds>", file=sys.stderr)
        return 2

    layout = db.Layout()
    layout.read(src)

    top = layout.cell(TOP)
    if top is None:
        print(f"ERROR: top cell {TOP!r} not found in {src}", file=sys.stderr)
        return 1

    bbox = top.dbbox()
    shift = db.Trans(
        int(round(SHIFT_X_UM / layout.dbu)), int(round(SHIFT_Y_UM / layout.dbu))
    )
    already = abs(bbox.left) < 0.01 and abs(bbox.bottom) < 0.01
    if not already:
        top.transform(shift)
        print(f"[INFO] shifted {TOP} by ({SHIFT_X_UM}, {SHIFT_Y_UM}) um")
    else:
        print(f"[INFO] {TOP} already at the origin")

    renamed = 0
    for layer_index in layout.layer_indexes():
        info = layout.get_info(layer_index)
        if (info.layer, info.datatype) not in TEXT_LAYERS:
            continue
        for cell in layout.each_cell():
            for shape in cell.shapes(layer_index).each():
                if not shape.is_text():
                    continue
                text = shape.text
                new = LABEL_RENAME.get(text.string)
                if new is None:
                    continue
                shape.text = db.Text(new, text.trans, text.size, text.font)
                renamed += 1
    print(f"[INFO] renamed {renamed} pin label(s)")

    print(f"[INFO] {TOP} bbox now {layout.cell(TOP).dbbox()}")

    layout.write(out)
    print(f"[INFO] wrote {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
