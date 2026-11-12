#!/usr/bin/env python3
"""WIP PCell-based 6T TG MUX2 generator.

Instantiates the PDK ``fet_n``/``fet_p`` PCells, relocates each gate pad to a
5.4 x 3.4 M1 pad with the CO and V1 side by side, routes S/n4 on M2 and gives
A/Y/B/S M1 landing pads with V1/M2 pins.

Current status (WIP, not flow-ready):
  * KLayout DRC: 17 items (GC.W1 at the gate-pad/poly junction, V1/M2
    alignment on the INV_N/INV_P gate pads, M1.S1 at the drain pads and
    M2.S1 at the n4/S crossings).
  * LVS extraction still merges A/B/S/Y into one net; the top-level M1/M2
    routing is shorting the signal pads or the gate V1s are not landing on
    the intended M2 verticals.
  * Not used by the library or the flow yet.

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

def b(x0,y0,x1,y1): return pya.Box(round(x0*1000),round(y0*1000),round(x1*1000),round(y1*1000))

def erase_box(cell, li, x0,y0,x1,y1):
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
        erase_box(c, GC, -1.3,1.7,1.3,4.3); erase_box(c, CO, -0.5,2.5,0.5,3.5); erase_box(c, M1, -1.3,1.7,1.3,4.3)
        c.shapes(GC).insert(b(-0.5, y0, 0.5, -1.7))
        c.shapes(GC).insert(b(-2.7, y0, -0.1, y0+3.4))
        c.shapes(CO).insert(b(-1.9, y0+1.2, -0.9, y0+2.2))
        c.shapes(M1).insert(b(-2.7, y0, 5.2, y0+3.4))
        c.shapes(V1).insert(b(2.8, y0+1.0, 4.2, y0+2.4))
    else:
        draw_fet(c, l=1.0, w=w, layer=AP_layer, e_cap=1.2, fnum=1, cont_between_gates=True, y_0='c')
        erase_box(c, GC, -1.3,2.6,1.3,5.2); erase_box(c, CO, -0.5,3.4,0.5,4.4); erase_box(c, M1, -1.3,2.6,1.3,5.2)
        c.shapes(GC).insert(b(-0.5, 2.6, 0.5, y0))
        c.shapes(GC).insert(b(-2.7, y0, -0.1, y0+3.4))
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

for cell,(x,y) in [(N1,(6,12)),(N2,(18,17)),(N3,(30,17)),(P1,(18,39)),(P2,(30,39)),(P3,(6,42))]:
    top.insert(pya.CellInstArray(cell.cell_index(), pya.Trans(pya.Vector(round(x*1000),round(y*1000)))))

# rails / taps / well / boundary
top.shapes(M1).insert(b(0,1.1,54,3.7)); top.shapes(M1).insert(b(0,55.7,54,58.3))
top.shapes(AP).insert(b(0,1.1,54,3.7)); top.shapes(AN).insert(b(0,55.7,54,58.3))
top.shapes(WN).insert(b(-6.3,29.4,60.3,63.4)); top.shapes(BD).insert(b(0,0,54,59.4))

# M1 straps and pins
top.shapes(M1).insert(b(14.7,17,17.3,39)); top.shapes(M1).insert(b(18.7,17,21.3,39))
top.shapes(M1).insert(b(26.7,17,29.3,39)); top.shapes(M1).insert(b(30.7,17,33.3,39))
top.shapes(M1).insert(b(13.5,27.9,16.9,31.3)); top.shapes(M1).insert(b(19.0,27.9,29.0,31.3))
top.shapes(M1).insert(b(30.7,27.9,34.1,31.3)); top.shapes(M1).insert(b(36.1,27.9,39.5,31.3))
top.shapes(M1).insert(b(7.5,9.9,10.9,15.9)); top.shapes(M1).insert(b(7.5,38.3,10.9,46.3))
top.shapes(M1).insert(b(1.9,10.7,5.3,12.5)); top.shapes(M1).insert(b(0.1,3.7,1.9,12.5)); top.shapes(M1).insert(b(0.1,10.7,2.7,13.3))
top.shapes(M1).insert(b(1.9,39.7,5.3,41.5)); top.shapes(M1).insert(b(0.1,39.7,1.9,55.7)); top.shapes(M1).insert(b(0.1,39.7,2.7,44.3))
# V1 pin/drain
for box in [(14.5,28.9,15.9,30.3),(23.0,28.9,24.4,30.3),(31.7,28.9,33.1,30.3),
            (37.1,28.9,38.5,30.3),(8.1,13.5,9.5,14.9),(8.1,43.5,9.5,44.9)]:
    top.shapes(V1).insert(b(*box))
# M2 S/n4
top.shapes(M2).insert(b(9.8,4.3,36.1,7.3)); top.shapes(M2).insert(b(9.8,53.0,36.1,56.0))
top.shapes(M2).insert(b(36.1,6.1,39.5,55.0))
top.shapes(M2).insert(b(6.5,13.5,22.8,16.5)); top.shapes(M2).insert(b(6.5,41.0,35.8,45.0))
top.shapes(M2).insert(b(6.5,13.5,11.2,45.0))
top.shapes(M2).insert(b(19.8,9.3,23.8,14.5)); top.shapes(M2).insert(b(31.8,45.0,35.8,50.9))
top.shapes(M2).insert(b(9.8,4.3,13.8,8.5)); top.shapes(M2).insert(b(31.8,7.3,35.8,12.7))
top.shapes(M2).insert(b(9.8,50.0,13.8,56.0)); top.shapes(M2).insert(b(19.8,47.0,23.8,53.0))
# M2 pins A/Y/B (S is the vertical)
top.shapes(M2).insert(b(13.5,27.9,16.9,31.3)); top.shapes(M2).insert(b(22.0,27.9,25.4,31.3))
top.shapes(M2).insert(b(30.7,27.9,34.1,31.3))
# labels
for t,x,y in [("VDD",2.7,57.1),("GND",2.7,2.4),("A",15.1,29.6),("Y",24.0,29.6),("B",32.4,29.6),("S",37.8,29.6)]:
    top.shapes(L1).insert(pya.Text(t,pya.Trans(pya.Vector(round(x*1000),round(y*1000)))))
for t,x,y in [("A",15.1,29.6),("Y",24.0,29.6),("B",32.4,29.6),("S",37.8,29.6)]:
    top.shapes(L2).insert(pya.Text(t,pya.Trans(pya.Vector(round(x*1000),round(y*1000)))))
top.flatten(1)
out = os.environ.get("TGMUX_PCELL_OUT", "tgmux_pcell.gds")
ly.write(out); print("wrote", out)
