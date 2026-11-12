#!/usr/bin/env python3
"""PCell-based 6T TG MUX2 generator (54.0 x 59.4).

Instantiates the PDK ``fet_n``/``fet_p`` PCells, removes the original gate
pad with a box-containment erase (the GC Paths are kept, which is what keeps
the active regions separate), relocates each gate pad to a 5.4 x 3.4 M1 pad
with CO/V1 side by side, routes S/n4 on M2 and gives A/Y/B/S M1 landing pads
with V1/M2 pins.

Status:
  * KLayout DRC: 0 items.
  * KLayout LVS extraction: A, B, S, Y, VDD, GND, six transistors, all
    signal pins independent.
  * The 54.0 um cell is wired into ``libs.ref/TR10_cmp_sc``.  The LEF adds
    two local M2 keep-outs around the internal S/n4 straps; the flow still
    exposes the n4 M2 wall to the expanded-guide router (see README).

Run with KLayout's Python::

    TGMUX_PCELL_OUT=/tmp/tgmux_pcell.gds \
        klayout -b -r flow/scripts/build_tgmux_pcell.py
"""
import os
import pya, sys
sys.path.insert(0, "libs.tech/klayout/tech/python")
from cells.util import draw_fet
from cells.layers_def import AP_layer, AN_layer

ly = pya.Layout(); ly.dbu = 0.001
top = ly.create_cell("MUXTG2")
AP = ly.layer(3, 1); AN = ly.layer(3, 2); GC = ly.layer(8, 1); CO = ly.layer(11, 0)
M1 = ly.layer(13, 0); V1 = ly.layer(19, 0); M2 = ly.layer(20, 0); WN = ly.layer(140, 0)
L1 = ly.layer(48, 0); L2 = ly.layer(49, 0); BD = ly.layer(235, 0)

def b(x0,y0,x1,y1): return pya.Box(round(x0*1000),round(y0*1000),round(x1*1000),round(y1*1000))

def erase_box(cell, li, x0,y0,x1,y1):
    """Erase only box shapes fully inside the rectangle (keep GC Paths)."""
    bb = b(x0,y0,x1,y1)
    for s in list(cell.shapes(li).each()):
        if not s.is_box():
            continue
        sb = s.box
        if bb.left <= sb.left and bb.bottom <= sb.bottom and sb.right <= bb.right and sb.top <= bb.top:
            cell.shapes(li).erase(s)

def make_fet(name, w, kind, y0):
    c = ly.create_cell(name)
    if kind == "N":
        draw_fet(c, l=1.0, w=w, layer=AN_layer, e_cap=1.2, fnum=1, cont_between_gates=True, y_0='c')
        erase_box(c, GC, -1.4,1.6,1.4,5.6); erase_box(c, CO, -0.6,3.6,0.6,4.8); erase_box(c, M1, -1.4,1.6,1.4,5.6)
        c.shapes(GC).insert(b(-0.5, y0, 0.5, -1.7))
        c.shapes(GC).insert(b(-2.7, y0, 0.5, y0+3.4))
        c.shapes(CO).insert(b(-1.9, y0+1.2, -0.9, y0+2.2))
        c.shapes(M1).insert(b(-2.7, y0, 5.2, y0+3.4))
        c.shapes(V1).insert(b(2.8, y0+1.0, 4.2, y0+2.4))
    else:
        draw_fet(c, l=1.0, w=w, layer=AP_layer, e_cap=1.2, fnum=1, cont_between_gates=True, y_0='c')
        erase_box(c, GC, -1.4,2.7,1.4,6.5); erase_box(c, CO, -0.6,4.5,0.6,5.7); erase_box(c, M1, -1.4,2.7,1.4,6.5)
        c.shapes(GC).insert(b(-0.5, 2.6, 0.5, y0))
        c.shapes(GC).insert(b(-2.7, y0, 0.5, y0+3.4))
        c.shapes(CO).insert(b(-1.9, y0+1.2, -0.9, y0+2.2))
        c.shapes(M1).insert(b(-2.7, y0, 5.2, y0+3.4))
        c.shapes(V1).insert(b(2.8, y0+1.0, 4.2, y0+2.4))
    return c

# subcells: NMOS new pad below active, PMOS above
N1 = make_fet("INV_N", 3.4, "N", -6.9)
N2 = make_fet("TG1_N", 3.4, "N", -7.7)
N3 = make_fet("TG2_N", 3.4, "N", -7.7)
P1 = make_fet("TG1_P", 5.2, "P", 8.0)
P2 = make_fet("TG2_P", 5.2, "P", 8.0)
P3 = make_fet("INV_P", 5.2, "P", 8.0)

for cell,(x,y) in [(N1,(6,12)),(N2,(18,17)),(N3,(31,17)),(P1,(18,39)),(P2,(31,39)),(P3,(6,42))]:
    top.insert(pya.CellInstArray(cell.cell_index(), pya.Trans(pya.Vector(round(x*1000),round(y*1000)))))

# rails / taps / well / boundary
top.shapes(M1).insert(b(0,1.1,54,3.7)); top.shapes(M1).insert(b(0,55.7,54,58.3))
top.shapes(AP).insert(b(0,1.1,54,3.7)); top.shapes(AN).insert(b(0,55.7,54,58.3))
# well/substrate taps to the rails (otherwise the PMOS bulk is a separate net)
for x in (2.2,7.6,13.0,18.4,23.8,29.2,34.6,40.0,45.4,50.8):
    top.shapes(CO).insert(b(x,1.9,x+1.0,2.9))
    top.shapes(CO).insert(b(x,56.5,x+1.0,57.5))
top.shapes(WN).insert(b(-6.3,29.4,60.3,63.4)); top.shapes(BD).insert(b(0,0,54,59.4))

# M1 straps and pins
top.shapes(M1).insert(b(15.1,17,16.9,39)); top.shapes(M1).insert(b(19.1,17,20.9,39))
top.shapes(M1).insert(b(28.1,17,29.9,39)); top.shapes(M1).insert(b(32.1,17,33.9,39))
top.shapes(M1).insert(b(13.5,27.9,16.9,31.3)); top.shapes(M1).insert(b(19.0,27.9,30.1,31.3))
top.shapes(M1).insert(b(32.1,27.9,35.5,31.3)); top.shapes(M1).insert(b(38.2,27.9,41.6,31.3))
top.shapes(M1).insert(b(6.7,9.9,10.9,15.9)); top.shapes(M1).insert(b(6.7,38.3,10.9,46.9))
top.shapes(M1).insert(b(1.9,10.7,5.3,12.5)); top.shapes(M1).insert(b(0.1,3.7,1.9,12.5)); top.shapes(M1).insert(b(0.1,10.7,2.7,13.3))
top.shapes(M1).insert(b(1.9,39.7,5.3,41.5)); top.shapes(M1).insert(b(0.1,39.7,1.9,55.7)); top.shapes(M1).insert(b(0.1,39.7,2.7,44.3))
# V1 pin/drain
for box in [(14.5,28.9,15.9,30.3),(23.0,28.9,24.4,30.3),(33.1,28.9,34.5,30.3),
            (39.2,28.9,40.6,30.3),(8.1,13.5,9.5,14.9),(8.1,44.5,9.5,45.9)]:
    top.shapes(V1).insert(b(*box))
# M2 S/n4
top.shapes(M2).insert(b(9.8,4.3,41.6,7.3)); top.shapes(M2).insert(b(9.8,53.2,41.6,56.2))
top.shapes(M2).insert(b(38.2,4.3,41.6,56.2))
top.shapes(M2).insert(b(6.5,12.0,22.8,15.0)); top.shapes(M2).insert(b(6.5,40.8,36.2,45.0))
top.shapes(M2).insert(b(6.5,12.5,11.2,46.9))
top.shapes(M2).insert(b(19.8,9.3,23.8,14.5)); top.shapes(M2).insert(b(32.8,45.0,36.2,50.9))
top.shapes(M2).insert(b(7.8,4.3,11.8,8.5)); top.shapes(M2).insert(b(32.8,7.1,36.2,12.7))
top.shapes(M2).insert(b(7.8,50.0,11.8,56.0)); top.shapes(M2).insert(b(19.8,47.0,23.8,53.4))
# M2 pins A/Y/B (S is the vertical)
top.shapes(M2).insert(b(13.5,27.9,16.9,31.3)); top.shapes(M2).insert(b(22.0,27.9,25.4,31.3))
top.shapes(M2).insert(b(32.1,27.9,35.5,31.3))
# labels
for t,x,y in [("VDD",2.7,57.1),("GND",2.7,2.4)]:
    top.shapes(L1).insert(pya.Text(t,pya.Trans(pya.Vector(round(x*1000),round(y*1000)))))
for t,x,y in [("A",15.2,29.6),("Y",23.7,29.6),("B",32.4,29.6),("S",39.9,29.6)]:
    top.shapes(L2).insert(pya.Text(t,pya.Trans(pya.Vector(round(x*1000),round(y*1000)))))
top.flatten(1)
out = os.environ.get("TGMUX_PCELL_OUT", "tgmux_pcell.gds")
ly.write(out); print("wrote", out)
