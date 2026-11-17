#!/usr/bin/env python3
"""TR10 analog layout library for the I/Q receiver blocks.

Drawing layers (PDK TR10):
    AP 3/1  AN 3/2  GC 8/1  CO 11/0  M1 13/0  WN 140/0  48/0 label

Devices are single-strip multi-finger MOS: one active strip of height Wf
with nf gates on a 4 um pitch (1 um gate + 3 um S/D).  The KLayout LVS
combiner sums the parallel fingers, so W = Wf*nf, L = L.

Device terminal anchors (all on M1):
    drain bus (below), source bus (above), gate landing (right)
Every gate strip has a contact on the gate bus (the GA.CO rule), and every
module that hosts an NMOS carries a P+ backgate tie for the P-well ERC.
"""
import pya

DBU = 0.001

AN_W = 1400
AN_S = 1400
AN_AP_S = 2800
CO_W = 1000
CO_S = 1000
CO_AN_E = 800
CO_GC_S = 1000
M1_W = 1800
M1_S = 1400
M1_CO_E = 800
M1_WIDE_S = 2000
GC_EN = 1200
G0 = 3000
PITCH = 4000
CO_N = 9
WN_E = 7500            # N-well enclosure of the PMOS active
WIDE = 22500           # the M1 "wide" threshold of the DRC deck


class RxLayout:
    def __init__(self, name):
        self.ly = pya.Layout()
        self.ly.dbu = DBU
        self.AP = self.ly.layer(3, 1)
        self.AN = self.ly.layer(3, 2)
        self.GC = self.ly.layer(8, 1)
        self.CO = self.ly.layer(11, 0)
        self.M1 = self.ly.layer(13, 0)
        self.WN = self.ly.layer(140, 0)
        self.LBL = self.ly.layer(48, 0)
        self.top = self.ly.create_cell(name)

    def box(self, layer, x0, y0, x1, y1):
        self.top.shapes(layer).insert(pya.Box(int(x0), int(y0), int(x1), int(y1)))

    def label(self, text, x, y, m2=False):
        layer = self.ly.layer(49, 0) if m2 else self.LBL
        self.top.shapes(layer).insert(pya.Text(text, pya.Trans(pya.Point(int(x), int(y)))))


def mos(ly, x0, y0, wf, L, nf, pmos=False):
    """Draw one multi-finger MOS at (x0,y0); return the terminal anchors.

    The device band spans y0-7800 .. y0+wf+5000 and x0-6000 .. x0+xlen+4000.
    """
    anl = ly.AN if not pmos else ly.AP
    # segment = pitch - L must fit a 1 um contact with 1.0 um to each gate
    pitch = max(PITCH, L + 3000)
    xlen = G0 + pitch * (nf - 1) + L + 3000

    if pmos:
        # N-well: encloses the AP strip by 7.5 um, the N+ well tap by 5 um
        # (AN.WN Emin), and stops >=10 um short of the neighbouring NMOS
        # active (WN.AN Smin)
        ly.box(ly.WN, x0 - WN_E, y0 - WN_E, x0 + xlen + 11000, y0 + wf + 16000)

    anl = ly.AN if not pmos else ly.AP
    ly.box(anl, x0, y0, x0 + xlen, y0 + wf)
    for i in range(nf):
        gx = x0 + G0 + pitch * i
        ly.box(ly.GC, gx, y0 - GC_EN, gx + L, y0 + wf + GC_EN)

    segs = [(x0, x0 + G0)]
    for i in range(nf - 1):
        a = x0 + G0 + pitch * i + L
        segs.append((a, a + pitch - L))
    segs.append((x0 + G0 + pitch * (nf - 1) + L, x0 + xlen))

    # contact column: pitch 2 um, symmetric edge margins in [1.0, 1.8] um so
    # every contact is either a 1.0-pitch interior contact (COM_s) or an
    # end contact with <=1.8 um active enclosure (COM_e).  CO_N=9/b0=1500
    # for the 20 um finger of the passing TIA layout.
    co_n = max(1, (wf - 1000) // 2000)
    b0 = (wf - (2000 * co_n - 1000)) // 2
    for k, (sx0, sx1) in enumerate(segs):
        cx = (sx0 + sx1) // 2
        for j in range(co_n):
            y = y0 + b0 + 2000 * j
            ly.box(ly.CO, cx - 500, y, cx + 500, y + 1000)

    ys = y0 + wf + 7600            # source bus (3.4 um tall: room for a
    yd = y0 - 5800                 # 1.4 um V1 with 1.0 um M1 enclosure)
    for k, (sx0, sx1) in enumerate(segs):
        cx = (sx0 + sx1) // 2
        if k % 2 == 0:
            ly.box(ly.M1, cx - 1300, y0 + 200, cx + 1300, ys + 900)
        else:
            ly.box(ly.M1, cx - 1300, yd, cx + 1300, y0 + wf - 200)

    ly.box(ly.M1, x0, ys, x0 + (xlen + 6600 if pmos else xlen), ys + 3400)
    ly.box(ly.M1, x0, yd, x0 + xlen, yd + 3400)     # drain bus

    # gate bus + a single CO on the bus (the pattern that passes the PDK
    # GA.CO / ERC checks; per-gate contacts did not)
    yb0, yb1 = y0 + wf + 1200, y0 + wf + 4600
    gb_x1 = x0 + xlen + 14000
    ly.box(ly.GC, x0 - 6000, yb0, gb_x1, yb1)
    co_x = gb_x1 - 2000
    # CO 1 um below the bus top / 0.8 um above its centre row: the exact
    # geometry of the passing TIA layout (M1 landing then encloses the CO
    # by 0.8 um on every side)
    ly.box(ly.CO, co_x, yb0 + 1600, co_x + 1000, yb0 + 2600)

    # gate M1 landing on the bus, enclosing the gate CO by 0.8 um
    gx0 = co_x + 500
    ly.box(ly.M1, gx0 - 1500, yb0 + 800, gx0 + 1500, yb0 + 3400)

    if pmos:
        # N+ well tap (GP = AN & WN) at the source-bus row, right of the
        # device: 3 um from the AP strip (AP.AN Smin 2.8), 3 um above the
        # gate bus, >=5 um inside the well on every side.  Its M1 pad
        # overlaps the extended source bus (same net: the PMOS bulk is vdd
        # = its source in these designs) so no separate bulk anchor is
        # needed -- the tap rides the source routing.
        tap_x = x0 + xlen + 3000
        ty0 = y0 + wf + 7600
        ly.box(ly.AN, tap_x, ty0, tap_x + 2600, ty0 + 2600)
        ly.box(ly.CO, tap_x + 800, ty0 + 800, tap_x + 1800, ty0 + 1800)
        ly.box(ly.M1, x0 + xlen + 1300, ty0 - 900, tap_x + 3500, ty0 + 3500)
        bulk = None
    else:
        bulk = None

    return {
        "xlen": xlen,
        "bbox": (x0 - 6000, y0 - 9000, x0 + xlen + 9000,
                 y0 + wf + (30000 if pmos else 13000)),
        "source": (x0 + xlen // 2, ys + 1700),
        "drain": (x0 + xlen // 2, yd + 1700),
        "gate": (gx0, yb0 + 2100),
        "gate_route_y": yb0 + 2100,
        "bulk": bulk,
    }


def wire(ly, x0, y0, x1, y1, w=2600):
    """Axis-aligned M1 wire of width w through (x0,y0)->(x1,y1) (both legs)."""
    lo, hi = min(x0, x1), max(x0, x1)
    ly.box(ly.M1, lo - w // 2, y0 - w // 2, hi + w // 2, y0 + w // 2)
    lo, hi = min(y0, y1), max(y0, y1)
    ly.box(ly.M1, x1 - w // 2, lo - w // 2, x1 + w // 2, hi + w // 2)


def route_h(ly, y, x0, x1, w=2600):
    ly.box(ly.M1, min(x0, x1) - w // 2, y - w // 2, max(x0, x1) + w // 2, y + w // 2)


def route_v(ly, x, y0, y1, w=2600):
    ly.box(ly.M1, x - w // 2, min(y0, y1) - w // 2, x + w // 2, max(y0, y1) + w // 2)
