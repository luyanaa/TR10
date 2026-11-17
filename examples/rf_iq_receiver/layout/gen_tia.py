#!/usr/bin/env python3
"""Generate the TR10 layout for the RX_TIA block of the I/Q receiver.

Run with KLayout's embedded python:
    klayout -b -z -r gen_tia.py

Geometry follows the PDK drawing layers and the KLayout DRC deck:
    AN 3/2  N+ active (NMOS)      GC 8/1  gate poly
    AP 3/1  P+ active (tap)       CO 11/0 contact 1x1
    M1 13/0 metal1               48/0  M1 label

The device is a single-strip multi-finger NMOS: one AN strip of height Wf
with nf gates on a 4 um pitch (1 um gate + 3 um S/D).  The LVS combiner sums
the parallel fingers, so the extracted device is W = Wf*nf, L = 1 um,
matching the schematic's `NMOS_nf w=200u l=1u nf=10`.
"""
import pya
import os

DBU = 0.001          # um per database unit
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "rx_tia.gds")

ly = pya.Layout()
ly.dbu = DBU
AN = ly.layer(3, 2)
AP = ly.layer(3, 1)
GC = ly.layer(8, 1)
CO = ly.layer(11, 0)
M1 = ly.layer(13, 0)
LBL = ly.layer(48, 0)

top = ly.create_cell("rx_tia_layout")


def box(layer, x0, y0, x1, y1):
    top.shapes(layer).insert(pya.Box(int(x0), int(y0), int(x1), int(y1)))


def label(layer, text, x, y):
    top.shapes(layer).insert(pya.Text(text, pya.Trans(pya.Point(int(x), int(y)))))


# ---------------------------------------------------------------- NMOS core
WF = 20000                     # W per finger (nm)
L = 1000                       # L (nm)
NF = 10
G0 = 3000
PITCH = 4000                   # 1 um gate + 3 um S/D
SEG_END = 3000
X_END = G0 + PITCH * (NF - 1) + L + SEG_END      # 43000
Y_TOP = WF

box(AN, 0, 0, X_END, Y_TOP)
for i in range(NF):
    gx = G0 + PITCH * i
    box(GC, gx, -1200, gx + L, Y_TOP + 1200)

# gate bus: 2.8 um tall so the 1 um gate CO keeps >=0.8 um of GC enclosure
GBUS_Y0, GBUS_Y1 = Y_TOP + 1200, Y_TOP + 4600
box(GC, -6000, GBUS_Y0, 57000, GBUS_Y1)

# S/D segments 0..NF, contacts centred (1.0 um from each gate)
segs = [(0, G0)]
for i in range(NF - 1):
    x0 = G0 + PITCH * i + L
    segs.append((x0, x0 + PITCH - L))
segs.append((G0 + PITCH * (NF - 1) + L, X_END))

CO_N = 9
cxs = []
for k, (x0, x1) in enumerate(segs):
    cx = (x0 + x1) // 2
    cxs.append(cx)
    for j in range(CO_N):
        # first/last contact within 1.8 um of the active edge (extraction
        # convention) and >=0.8 um of AN enclosure
        y = 1500 + 2000 * j
        box(CO, cx - 500, y, cx + 500, y + 1000)

# interdigitated M1: even segments to the source bus, odd to the drain bus
for k, (x0, x1) in enumerate(segs):
    cx = cxs[k]
    if k % 2 == 0:
        box(M1, cx - 1300, 200, cx + 1300, 24000)
    else:
        box(M1, cx - 1300, -4000, cx + 1300, 19800)

box(M1, 0, 24000, X_END, 25800)          # VSS (source) bus
box(M1, 0, -5800, X_END, -4000)          # OUT (drain) bus

# gate contact + landing
box(CO, 55000, 22800, 56000, 23800)
box(M1, 54000, 22000, 57000, 24600)

# ---------------------------------------------------------------- pads
def pad(name, x0, y0, x1, y1):
    box(M1, x0, y0, x1, y1)
    label(LBL, name, x0 + 1000, y0 + 1000)


# Pads shrunk 30x30 -> 16x16 um after PEX1: with areacap metal1 = 35 aF/um^2
# each 30x30 pad alone contributes ~31 fF, which dominated IN and OUT.
box(M1, 12000, 25800, 14600, 38000)
pad("VSS", 0, 36000, 16000, 52000)

box(M1, X_END, -5800, 52000, -4000)
box(M1, 47400, -18000, 52600, -3800)
pad("OUT", 50000, -18000, 66000, -2000)

box(M1, 54700, 23500, 57300, 28000)
box(M1, 54700, 25400, 61600, 28000)
pad("IN", 59000, 25400, 75000, 41400)

# P+ backgate tap in the P-well, tied to VSS
box(AP, 32000, 36000, 35000, 39000)
box(CO, 33000, 37000, 34000, 38000)
box(M1, 15000, 36000, 35000, 39500)

ly.write(OUT)
print("wrote", OUT)
print("cells", ly.cells(), "bbox", top.bbox())
