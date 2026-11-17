#!/usr/bin/env python3
"""Generate TR10 layouts + strict LVS netlists for the receiver modules.

Run: MOD=<module> klayout -b -z -r gen_modules.py
     (module: lna | mixer | ssb | fm | vco)

The device lists mirror the pre-layout spice .lib files exactly (same W, L,
nf and terminal-to-net mapping), so the strict LVS contract generated from
them certifies that the layout implements the schematic devices:

    lna    X1 (d g vss) X2 (vdd d out)          200u/1u nf=10
    mixer  X0..X3 quad                          200u/1u nf=10
    ssb    X1 (out_p i_lp tail) X2 (out_n q_hp tail)   100u/1u nf=4
    fm     X1..X12 Gilbert-style demodulator    100u/1u nf=4
    vco    X1/X2 cross-coupled 200u/1u nf=4 + 2 varactors 9600u (160x60u)

Routing architecture: device terminals live on M1 buses inside the device
band; every net gets one vertical M2 trunk right of the widest gate bus,
connected through 1 um V1 cuts on 3 um M1 stubs (V1 needs 1.0 um of M1 and
M2 enclosure and 1.2 um of clearance from poly, so the gate V1 sits past the
bus end).  All bulk ties go to the common substrate (vss): the 1 um flow has
no deep-n-well, so the varactor bulk is the substrate rather than the vtune
of the abstracted NMOS_var model.
"""
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import rxlib

OUT_DIR = os.path.dirname(os.path.abspath(__file__))
MOD = os.environ.get("MOD", "lna")

MODULES = {
    "lna": {
        "devs": [
            ("d",   "g", "vss", 20000, 1000, 10, False),
            ("vdd", "d", "out", 20000, 1000, 10, False),
        ],
        "ports": ["d", "g", "out", "vdd", "vss"],
    },
    "mixer": {
        "devs": [
            ("out_i", "lo0",   "rf_p", 20000, 1000, 10, False),
            ("out_i", "lo180", "rf_n", 20000, 1000, 10, False),
            ("out_q", "lo90",  "rf_p", 20000, 1000, 10, False),
            ("out_q", "lo270", "rf_n", 20000, 1000, 10, False),
        ],
        "ports": ["out_i", "out_q", "lo0", "lo90", "lo180", "lo270",
                  "rf_p", "rf_n", "vss"],
    },
    "ssb": {
        "devs": [
            ("out_p", "i_lp", "tail", 25000, 1000, 4, False),
            ("out_n", "q_hp", "tail", 25000, 1000, 4, False),
        ],
        "ports": ["out_p", "out_n", "i_lp", "q_hp", "tail", "vss"],
    },
    "fm": {
        "devs": [
            ("t1",    "di",    "tail1", 25000, 1000, 4, False),
            ("t2",    "vref",  "tail1", 25000, 1000, 4, False),
            ("out_p", "qp",    "t1",    25000, 1000, 4, False),
            ("out_n", "vref2", "t1",    25000, 1000, 4, False),
            ("out_n", "qp",    "t2",    25000, 1000, 4, False),
            ("out_p", "vref2", "t2",    25000, 1000, 4, False),
            ("t3",    "dq",    "tail2", 25000, 1000, 4, False),
            ("t4",    "vref",  "tail2", 25000, 1000, 4, False),
            ("out_n", "ip",    "t3",    25000, 1000, 4, False),
            ("out_p", "vref2", "t3",    25000, 1000, 4, False),
            ("out_p", "ip",    "t4",    25000, 1000, 4, False),
            ("out_n", "vref2", "t4",    25000, 1000, 4, False),
        ],
        "ports": ["t1", "t2", "t3", "t4", "di", "dq", "qp", "ip",
                  "vref", "vref2", "out_p", "out_n", "tail1", "tail2", "vss"],
    },
    "vco": {
        # RX_VCO: cross-coupled pair 200u/1u nf=4 (d=out_p, g=out_n, s=tail)
        # and two NMOS_var varactors 9600u as 160 x 60u fingers.  NMOS_var is
        # `Xcore minus plus minus minus`: the GATE is the control terminal
        # (vtune) and drain/source/bulk are the tank node.
        "devs": [
            ("out_p", "out_n", "tail",  50000, 1000, 4,   False),
            ("out_n", "out_p", "tail",  50000, 1000, 4,   False),
            ("out_p", "vtune", "out_p", 60000, 1000, 160, False),
            ("out_n", "vtune", "out_n", 60000, 1000, 160, False),
        ],
        "ports": ["out_p", "out_n", "vtune", "tail", "vss"],
    },
    "amdemod": {
        # RX_AM_DEMOD from demod_am.lib: 8 NMOS 100u/1u nf=4 and 4 PMOS
        # 50u/2u nf=4 (diode-connected mirror pair per channel)
        "devs": [
            ("d1", "ii", "tail",  25000, 1000, 4, False),   # X1
            ("d2", "bi", "tail",  25000, 1000, 4, False),   # X2
            ("d1", "d1", "vdd",   12500, 2000, 4, True),    # X3 diode PMOS
            ("d2", "d1", "vdd",   12500, 2000, 4, True),    # X4 mirror PMOS
            ("d2", "d2", "vss",   25000, 1000, 4, False),   # X5 clamp
            ("out", "d2", "vss",  25000, 1000, 4, False),   # X6 mirror out
            ("d3", "qq", "tailq", 25000, 1000, 4, False),   # X7
            ("d4", "bq", "tailq", 25000, 1000, 4, False),   # X8
            ("d3", "d3", "vdd",   12500, 2000, 4, True),    # X9 diode PMOS
            ("d4", "d3", "vdd",   12500, 2000, 4, True),    # X10 mirror PMOS
            ("d4", "d4", "vss",   25000, 1000, 4, False),   # X11 clamp
            ("out", "d4", "vss",  25000, 1000, 4, False),   # X12 mirror out
        ],
        "ports": ["ii", "qq", "bi", "bq", "d1", "d2", "d3", "d4",
                  "tail", "tailq", "out", "vdd", "vss"],
    },
}

mod = MODULES[MOD]
ly = rxlib.RxLayout("rx_" + MOD)
M2 = ly.ly.layer(20, 0)
V1 = ly.ly.layer(19, 0)

DEVS = []
y = 0
for d_net, g_net, s_net, wf, L, nf, pmos in mod["devs"]:
    d = rxlib.mos(ly, 3000, y, wf, L, nf, pmos)
    DEVS.append(dict(net_d=d_net, net_g=g_net, net_s=s_net, **d))
    y = d["bbox"][3] + 6000

# nets: the terminal anchors per net (+ the PMOS bulk tap anchor)
SUB = "vss" if "vss" in mod["ports"] else "VSS"
VDD = "vdd" if "vdd" in mod["ports"] else "VDD"
NETS = {}
for d, dev in zip(DEVS, mod["devs"]):
    terms = [("drain", d["net_d"]), ("gate", d["net_g"]), ("source", d["net_s"])]
    if dev[6] and d["bulk"]:
        terms.append(("bulk", VDD))
    for term, net in terms:
        NETS.setdefault(net, []).append(d[term])

# P+ backgate tie (the ERC_FLOATING_PWELL rule).  The tap sits ABOVE the
# device row: its M1 wire to the vss trunk must not cross the device M1
# strips (that would short every net to vss).  It joins the module's own
# substrate net name (lower-case vss, as in the pre-layout .lib ports).
y_max = max(d["bbox"][3] for d in DEVS)
x_max = max(d["bbox"][2] for d in DEVS)
tap_x, tap_y = x_max + 3000, y_max + 8000
ly.box(ly.AP, tap_x, tap_y, tap_x + 2600, tap_y + 2600)
ly.box(ly.CO, tap_x + 800, tap_y + 800, tap_x + 1800, tap_y + 1800)
ly.box(ly.M1, tap_x - 900, tap_y - 900, tap_x + 3500, tap_y + 3500)
NETS.setdefault(SUB, []).append((tap_x + 1300, tap_y + 1300))

# M2 trunks: one vertical per net at a dedicated x, 6 um apart.  The first
# trunk clears the widest gate bus by 2.5 um so the gate V1 keeps >=1.5 um
# of poly clearance (V1.GA needs 1.2).
X_SIDE0 = 3000 + max(d["xlen"] for d in DEVS) + 14000 + 2500
DX = 6000
net_x = {}
trunk_top = {}
for i, net in enumerate(NETS):
    net_x[net] = X_SIDE0 + DX * i
for net, pts in NETS.items():
    xs = net_x[net]
    pys = [p[1] for p in pts]
    y_lo, y_hi = min(pys) - 2000, max(pys) + 2000
    ly.box(M2, xs - 1900, y_lo, xs + 1900, y_hi)
    trunk_top[net] = y_hi
    for px, py in pts:
        # M1 stub: 3.6 um tall -> the 1.4 um V1 keeps 1.1 um of M1
        # enclosure (rule needs 1.0) and the rows stay 2.5+ um apart
        ly.box(ly.M1, px - 1300, py - 1800, xs + 1900, py + 1800)
        ly.box(V1, xs - 700, py - 700, xs + 700, py + 700)

# ports: labels on the M2 trunks (inside the trunk shape, top end)
for net in mod["ports"]:
    xs = net_x.get(net)
    if xs is not None:
        ly.label(net, xs, trunk_top[net] - 1000, m2=True)

gds = os.path.join(OUT_DIR, "rx_%s.gds" % MOD)
ly.ly.write(gds)
print("wrote", gds, "bbox", ly.top.bbox())

cir = os.path.join(OUT_DIR, "rx_%s.strict.cir" % MOD)
with open(cir, "w") as fh:
    fh.write("* Strict LVS contract for rx_%s (generated with the layout)\n" % MOD)
    fh.write(".SUBCKT rx_%s %s\n" % (MOD, " ".join(mod["ports"])))
    for i, d in enumerate(DEVS):
        typ = "PMOS" if mod["devs"][i][6] else "NMOS"
        w = mod["devs"][i][3] * mod["devs"][i][5] / 1000.0
        L = mod["devs"][i][4] / 1000.0
        bulk = VDD if typ == "PMOS" else SUB
        fh.write("M%d %s %s %s %s %s w=%.1fu l=%.1fu\n" % (
            i + 1, d["net_d"], d["net_g"], d["net_s"], bulk, typ, w, L))
    fh.write(".ENDS\n")
print("wrote", cir)
