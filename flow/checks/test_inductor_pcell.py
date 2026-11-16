#!/usr/bin/env python3
"""Build and inspect the TR10 spiral inductor PCell.

Run with KLayout::

    klayout -b -r flow/checks/test_inductor_pcell.py

Two things are checked:

  1. the cell is registered in the shipped TR10 PCell library (that is the
     path the GUI uses, via pymacros/TR10_libraries.lym);
  2. the geometry it produces matches the shared geometry module and the
     DRC minimums (M2 width >= 3.4 for the V1 landing, M2 space >= 2.0,
     V1 exactly 1.4 x 1.4).

The TR10 library is bound to the TR10 technology, which does not exist in
batch mode, so KLayout cannot resolve it by name here.  The instance test
therefore registers the same PCell class in a technology-free scratch
library; the registration check above still covers __init__.py.

One single-top-cell GDS per case is written to $IND_OUT_DIR (default
/tmp/opencode/ind_pcell).  KLayout drops an un-instantiated PCell cell on
write, so each case is wrapped in a plain TOP cell.  Exit 0 on success.
"""
import os
import sys

import pya

PDK = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, os.path.join(PDK, "libs.tech/klayout/tech/python"))

from cells import tr_1um                                   # noqa: E402
from cells.inductor import inductor_spiral                 # noqa: E402
from cells.inductor_geom import geometry, wheeler_nh       # noqa: E402

fail = 0

# ---- 1. registration -----------------------------------------------------
tr_1um("TR10")
tr10 = None
for lid in pya.Library.library_ids():
    lib = pya.Library.library_by_id(lid)
    if lib is not None and lib.name() == "TR10":
        tr10 = lib
        break
if tr10 is None:
    print("FAIL: TR10 library was not registered")
    sys.exit(1)
names = list(tr10.layout().pcell_names())
print("TR10 PCells: %s" % ", ".join(sorted(names)))
if "inductor_spiral" not in names:
    print("FAIL: inductor_spiral is not registered in the TR10 library")
    fail = 1

outdir = os.environ.get("IND_OUT_DIR", "/tmp/opencode/ind_pcell")
os.makedirs(outdir, exist_ok=True)


def build(cell_name, params, gds_name):
    """Instantiate the PCell in a fresh library and write a single-top GDS."""
    lib = pya.Library()
    lib.description = "TR10 inductor PCell check"
    lib.layout().dbu = 0.001
    lib.layout().register_pcell("inductor_spiral", inductor_spiral())
    lib.register("TR10_IND_%s" % gds_name)
    ly = lib.layout()
    c = ly.create_cell("inductor_spiral", params)
    c.name = cell_name
    top = ly.create_cell(cell_name + "_TOP")
    top.insert(pya.CellInstArray(c.cell_index(), pya.Trans()))
    ly.write(os.path.join(outdir, "ind_%s.gds" % gds_name))
    return ly, c


CASES = [
    # name, turns, d_out, width, spacing
    ("IND_4T_250U", 4, 250.0, 8.0, 3.0),
    ("IND_2T_150U", 2, 150.0, 8.0, 3.0),
]

for name, turns, d_out, w, s in CASES:
    ly, c = build(name,
                  {"turns": turns, "d_out": d_out, "width": w, "spacing": s},
                  name)
    M1, V1, M2 = ly.layer(13, 0), ly.layer(19, 0), ly.layer(20, 0)
    bb = c.dbbox()
    g = geometry(turns, d_out, w, s)
    print("=== %s ===" % name)
    print("  bbox   : %.3f %.3f %.3f %.3f um  (%.1f x %.1f)"
          % (bb.left, bb.bottom, bb.right, bb.top, bb.width(), bb.height()))
    print("  shapes : M1=%d M2=%d V1=%d"
          % (c.shapes(M1).size(), c.shapes(M2).size(), c.shapes(V1).size()))
    print("  model  : L=%.4f nH  Rdc=%.3f ohm  d_in=%.2f um  len_M2=%.1f um"
          % (wheeler_nh(turns, d_out, w, s), g["r_dc_ohm"],
             g["d_in_um"], g["length_m2_um"]))
    if abs(bb.width() - d_out) > 1e-6:
        print("  FAIL: bbox width %.3f != d_out %.3f" % (bb.width(), d_out))
        fail = 1
    if bb.height() <= d_out:
        print("  FAIL: pads did not extend the bbox below the spiral")
        fail = 1
    if c.shapes(V1).size() != 2:
        print("  FAIL: expected 2 V1 cuts, found %d" % c.shapes(V1).size())
        fail = 1
    m2r = pya.Region(c.shapes(M2))
    if m2r.width_check(3400).count():
        print("  FAIL: M2 narrower than 3.4 um")
        fail = 1
    if m2r.space_check(2000).count():
        print("  FAIL: M2 spacing below 2.0 um")
        fail = 1
    for sh in c.shapes(V1).each():
        bx = sh.box
        if bx.width() != 1400 or bx.height() != 1400:
            print("  FAIL: V1 %s is not 1.4 x 1.4 um" % bx)
            fail = 1

# ---- 3. parameter coercion ----------------------------------------------
ly, c = build("IND_COERCED",
              {"turns": 3, "d_out": 100.0, "width": 2.0, "spacing": 0.5},
              "IND_COERCED")
M2 = ly.layer(20, 0)
m2r = pya.Region(c.shapes(M2))
print("=== IND_COERCED (asked width=2.0, spacing=0.5) ===")
print("  M2 shapes=%d  width<3.4 violations=%d  space<2.0 violations=%d"
      % (c.shapes(M2).size(), m2r.width_check(3400).count(),
         m2r.space_check(2000).count()))
# pcell_parameter() reports the raw value, so coercion is proven on the
# produced geometry: if width had stayed 2.0 the M2 width check would fire.
if c.shapes(M2).size() == 0:
    print("  FAIL: coercion left the cell empty")
    fail = 1
if m2r.width_check(3400).count() != 0:
    print("  FAIL: width was not coerced to the V1 landing minimum 3.4")
    fail = 1
if m2r.space_check(2000).count() != 0:
    print("  FAIL: spacing was not coerced to M2.S1 = 2.0")
    fail = 1

print("\nwrote GDS files to %s" % outdir)
print("RESULT: %s" % ("FAIL" if fail else "PASS"))
sys.exit(fail)
