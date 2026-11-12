#!/usr/bin/env python3
"""Build libs.ref/TR10_cmp_sc/gds/TR10_cmp_sc.gds from the pinned C4004 source.

Run with KLayout's Python (the system Python has no ``klayout.db``)::

    CMP_GDS_SRC=libs.ref/TR10_cmp_sc/src/TR-1um_STDCELL.gds \
    CMP_GDS_OUT=libs.ref/TR10_cmp_sc/gds/TR10_cmp_sc.gds \
        klayout -b -r flow/scripts/build_cmp_sc_gds.py

Transformations, all of which are deliberate:

* 48/0 power labels ``vdd``/``vss`` are renamed to ``VDD``/``GND`` so the
  KLayout LVS extraction and the LibreLane power pins use the PDK names.
* Internal flip-flop node labels (CKP/CKB/QM/QS) are removed.  KLayout's
  hierarchical LVS promotes every label inside an instantiated cell to a
  subcircuit port; leaving them makes the extracted DFF port list disagree
  with both the LEF and the checked-in SPICE.  They are debug names only.
* The C4004 ``via_1`` helper cell (used only by its custom router) is dropped.
* Metal-only TIEHI/TIELO cells are added.  The TR-10 process expresses a
  constant as an M1 strap from the appropriate rail; the LVS contract builder
  aliases the tied net to the physical supply, so no device model is needed.
  They are two sites wide so the strap keeps >= 3.4 um M1 clearance from the
  neighbouring cell; a one-site tie would violate M1.S1 in a dense row.
* The n-well (140/0) is *not* shifted.  The source GDS draws it with a
  6.3 um halo on each side (and 4 um above the row top) so that abutting cells
  merge into one well and the well still encloses the edge PMOS.  Removing
  the negative-x halo would make the well edge coincide with the PMOS active
  edge and fail the enclosure rule.
"""

from __future__ import annotations

import os

import pya


LAYER = {
    "M1": (13, 0),
    "V1": (19, 0),
    "M2": (20, 0),
    "WN": (140, 0),
    "PRB": (235, 0),
    "M1_LBL": (48, 0),
    "M2_LBL": (49, 0),
}

ROW_H = 59.4
SITE_W = 5.4
TIE_W = 2 * SITE_W

VDD_LO, VDD_HI = 55.7, 58.3
GND_LO, GND_HI = 1.1, 3.7
WN_LO, WN_HI = 29.6, 63.4
WN_HALO = 6.3


def box(x0: float, y0: float, x1: float, y1: float) -> pya.Box:
    return pya.Box(round(x0 * 1000), round(y0 * 1000), round(x1 * 1000), round(y1 * 1000))


def add_box(cell: pya.Cell, layer: pya.LayerInfo, coords) -> None:
    cell.shapes(layer).insert(box(*coords))


def add_label(cell: pya.Cell, layer: pya.LayerInfo, text: str, x: float, y: float) -> None:
    cell.shapes(layer).insert(pya.Text(text, pya.Trans(round(x * 1000), round(y * 1000))))


def build_tie(layout: pya.Layout, name: str, high: bool) -> pya.Cell:
    cell = layout.create_cell(name)
    m1 = layout.layer(*LAYER["M1"])
    wn = layout.layer(*LAYER["WN"])
    prb = layout.layer(*LAYER["PRB"])
    lbl = layout.layer(*LAYER["M1_LBL"])

    add_box(cell, prb, (0.0, 0.0, TIE_W, ROW_H))
    # Same well halo as the logic cells so a tie never opens a WN gap.
    add_box(cell, wn, (-WN_HALO, WN_LO, TIE_W + WN_HALO, WN_HI))
    add_box(cell, m1, (0.0, VDD_LO, TIE_W, VDD_HI))
    add_box(cell, m1, (0.0, GND_LO, TIE_W, GND_HI))

    if high:
        # Strap from the VDD rail down to an M1 pin pad in the middle of the cell.
        add_box(cell, m1, (3.4, 42.7, 6.4, VDD_LO))
    else:
        add_box(cell, m1, (3.4, GND_HI, 6.4, 16.2))

    add_label(cell, lbl, "VDD", TIE_W / 2, (VDD_LO + VDD_HI) / 2)
    add_label(cell, lbl, "GND", TIE_W / 2, (GND_LO + GND_HI) / 2)
    return cell


def build_edff(layout: pya.Layout) -> None:
    """EDFF = the EDFFRB layout as-is; the netlist ties RSTB high."""
    source = layout.cell("EDFFRB")
    if source is None:
        return
    target = layout.create_cell("EDFF")
    target.copy_tree(source)


def build_dff2(layout: pya.Layout) -> None:
    """Two DFFs side by side with a shared CK pin (M2 strap in the CK band)."""
    source = layout.cell("DFF")
    if source is None:
        return
    target = layout.create_cell("DFF2")
    ci = source.cell_index()
    target.insert(pya.CellInstArray(ci, pya.Trans(pya.Vector(0, 0))))
    target.insert(pya.CellInstArray(ci, pya.Trans(pya.Vector(64800, 0))))
    # join the two CK pins (y 50.9..54.3); the D/Q/QB pins are at y 27.9..31.3
    target.shapes(layout.layer(20, 0)).insert(pya.Box(6400, 50900, 74600, 54300))
    # DFF2-level pin labels (the sub-DFF labels stay inside the DFF cells;
    # the LVS needs the macro pins labelled on the DFF2 cell itself).
    labels = {
        48: [("VDD", 2700, 57100), ("GND", 2700, 2400)],
        49: [
            ("CK", 8100, 52700),
            ("D0", 13500, 29700), ("Q0", 62100, 29700), ("QB0", 56700, 29700),
            ("D1", 13500 + 64800, 29700), ("Q1", 62100 + 64800, 29700),
            ("QB1", 56700 + 64800, 29700),
        ],
    }
    for layer, texts in labels.items():
        for text, x, y in texts:
            target.shapes(layout.layer(layer, 0)).insert(
                pya.Text(text, pya.Trans(pya.Vector(x, y)))
            )


def build_feedthru(layout: pya.Layout) -> None:
    """One-site feedthrough: M1 rails + N-well + a full-height M2 strap."""
    target = layout.create_cell("FEEDTHRU")
    wn = layout.layer(140, 0)
    m1 = layout.layer(13, 0)
    m2 = layout.layer(20, 0)
    target.shapes(wn).insert(pya.Box(-6300, 29600, 11700, 63400))
    target.shapes(m1).insert(pya.Box(0, 1100, 5400, 3700))
    target.shapes(m1).insert(pya.Box(0, 55700, 5400, 58300))
    target.shapes(m2).insert(pya.Box(1000, 0, 4400, 59400))
    for layer, text, x, y in [
        (48, "VDD", 2700, 57100),
        (48, "GND", 2700, 2400),
        (49, "A", 2700, 29700),
    ]:
        target.shapes(layout.layer(layer, 0)).insert(
            pya.Text(text, pya.Trans(pya.Vector(x, y)))
        )


def build_tgmux(layout: pya.Layout) -> None:
    """6T transmission-gate MUX core (experimental, 21.6 um).

    The MUX2 middle row contains two transmission gates (MP3/MN2 and MP4/MN3)
    plus the S inverter (MP0/MN5); the other six devices are input/output
    inverters.  This keeps only the 6T core and trims the middle active to the
    shared S/D at x 5.8..16.4.  The original S pin is outside the 21.6 um
    cell, so a new S GC pad/CO/M1 pad is added; an n4 M1 bridge and an A pin
    bridge complete the connectivity.  All signal pins are on M1.

    The cell is DRC-clean and extracts the intended 6T netlist, but the
    detailed router cannot access the in-cell M1 B pin (DRT-0073); a new
    pin-access layout is required before it can be used in the flow.
    """
    src = layout.cell("MUX2")
    if src is None:
        return
    dst = layout.create_cell("MUXTG2")
    W = 21600
    ap = layout.layer(3, 1); an = layout.layer(3, 2); gc = layout.layer(8, 1)
    co = layout.layer(11, 0); m1 = layout.layer(13, 0); nw = layout.layer(140, 0)
    lbl = layout.layer(48, 0); bd = layout.layer(235, 0)

    def reg(layer, datatype):
        return pya.Region(src.begin_shapes_rec(layout.layer(layer, datatype)))

    for layer, datatype in ((3, 1), (3, 2)):
        r = reg(layer, datatype)
        mid = r & pya.Region(pya.Box(0, 15000, W, 43000))
        tb = r - pya.Region(pya.Box(0, 15000, W, 43000))
        mid &= pya.Region(pya.Box(5800, 15000, 16400, 43000))
        tb &= pya.Region(pya.Box(0, 0, W, 59400))
        dst.shapes(layout.layer(layer, datatype)).insert(mid + tb)

    keep = pya.Region()
    for poly in reg(8, 1).each():
        b = poly.bbox()
        if 1000 <= b.left and b.right <= 6000 and b.bottom < 16000 and b.top > 42000:
            continue
        if 16000 <= b.left and b.right <= 20000 and b.bottom < 16000 and b.top > 42000:
            continue
        if b.left >= 12000 and b.right > 24000:
            continue
        if 9800 <= b.left and b.right <= 12400 and b.bottom >= 46600 and b.top <= 49200:
            continue
        keep.insert(poly)
    keep &= pya.Region(pya.Box(0, 0, 20800, 59400))
    dst.shapes(gc).insert(keep)

    for layer in (co, m1):
        dst.shapes(layer).insert(pya.Region(src.begin_shapes_rec(layer)) & pya.Region(pya.Box(0, 0, W, 59400)))

    co_reg = pya.Region(dst.shapes(co))
    allowed = pya.Region(dst.shapes(ap)) + pya.Region(dst.shapes(an)) + pya.Region(dst.shapes(gc))
    co_reg -= (co_reg - allowed)
    dst.shapes(co).clear(); dst.shapes(co).insert(co_reg)

    m1_reg = pya.Region(dst.shapes(m1))
    for x0, y0, x1, y1 in (
        (9800, 41700, 12400, 49200),
        (17000, 25100, 21600, 27700),
        (17800, 36700, 21600, 41700),
        (17800, 16600, 21600, 19300),
        (5800, 47800, 8400, 48200),
    ):
        m1_reg -= pya.Region(pya.Box(x0, y0, x1, y1))
    m1_reg += pya.Region(pya.Box(16200, 51000, 17800, 52800))
    m1_reg += pya.Region(pya.Box(17800, 13800, 19600, 52800))
    m1_reg += pya.Region(pya.Box(4400, 28000, 5800, 31000))
    m1_reg += pya.Region(pya.Box(6000, 43100, 11200, 46500))
    dst.shapes(m1).clear(); dst.shapes(m1).insert(m1_reg)

    dst.shapes(gc).insert(pya.Box(8600, 43100, 11200, 45700))
    dst.shapes(co).insert(pya.Box(9400, 43900, 10400, 44900))
    dst.shapes(nw).insert(pya.Region(pya.Box(-6300, 29600, W + 6300, 63400)))
    dst.shapes(bd).insert(pya.Box(0, 0, W, 59400))
    for text, x, y in (
        ("VDD", 2700, 57100), ("GND", 2700, 2400),
        ("A", 2700, 29600), ("Y", 11100, 29600),
        ("B", 15100, 29600), ("S", 8600, 44800),
    ):
        dst.shapes(lbl).insert(pya.Text(text, pya.Trans(pya.Vector(x, y))))

def main() -> int:
    source = os.environ["CMP_GDS_SRC"]
    output = os.environ["CMP_GDS_OUT"]

    layout = pya.Layout()
    layout.read(source)
    layout.dbu = 0.001

    # Drop the router helper cell; it is not a standard cell.
    via_cell = layout.cell("via_1")
    if via_cell is not None:
        layout.delete_cell(via_cell.cell_index())

    # Rename the power labels everywhere and drop the internal-node labels.
    # Text is copied into each cell, so walk the shapes, not only the top cell.
    internal = {"CKP", "CKB", "QM", "QS"}
    for cell in layout.each_cell():
        for layer_index in layout.layer_indexes():
            for shape in list(cell.shapes(layer_index).each()):
                if not shape.is_text():
                    continue
                text = shape.text
                low = text.string.lower()
                if low in {"vdd", "vcc"}:
                    shape.text = pya.Text("VDD", text.trans)
                elif low in {"vss", "gnd"}:
                    shape.text = pya.Text("GND", text.trans)
                elif text.string in internal:
                    cell.shapes(layer_index).erase(shape)

    build_tie(layout, "TIEHI", high=True)
    build_tie(layout, "TIELO", high=False)
    build_edff(layout)
    build_dff2(layout)
    build_feedthru(layout)
    pcell_gds = os.environ.get("TGMUX_PCELL_GDS")
    if pcell_gds:
        layout.read(pcell_gds)
    else:
        build_tgmux(layout)

    layout.write(output)
    print(f"wrote {output}: {layout.cells()} cells")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
