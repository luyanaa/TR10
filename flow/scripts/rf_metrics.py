#!/usr/bin/env python3
"""Extract f_T / f_MAX of the TR10 MOS devices and the sign of the spiral
inductor one-port Q.

Everything here is an ngspice small-signal extraction on the *existing*
models; no parameter is fitted.  The point is to make the RF figures
reproducible instead of quoting hand calculations:

  * f_T   : frequency where |h21| = |y21/y11| falls to 1 (output shorted)
  * f_MAX : frequency where Mason's unilateral gain U falls to 1
  * Q     : Im(Zin)/Re(Zin) for the pi-model inductor, for a shorted,
            50 ohm and open second port

Mason's gain needs all four y parameters, so each bias point is run twice:
once with the gate driven and the drain AC-grounded, once the other way
round.  ngspice's `wrdata` writes complex vectors as real/imag pairs.

Usage:
    python3 flow/scripts/rf_metrics.py
    python3 flow/scripts/rf_metrics.py --json
"""
from __future__ import annotations

import argparse
import json
import math
import os
import subprocess
import sys

PDK = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
MODELS = os.path.join(PDK, "libs.tech/ngspice/models")
INC = (f".include {MODELS}/ip62_models_calibrated\n"
       f".include {MODELS}/models_IP62_mos_rf.lib\n")


# --------------------------------------------------------------------------
# ngspice helpers
# --------------------------------------------------------------------------
def _ngspice(netlist: str, workdir: str = "/tmp") -> str:
    os.makedirs(workdir, exist_ok=True)
    path = os.path.join(workdir, "rf_metrics.sp")
    with open(path, "w") as fh:
        fh.write(netlist)
    out = subprocess.run(["ngspice", "-b", path], cwd=workdir,
                         capture_output=True, text=True).stdout
    return out


def _read_wrdata(path: str):
    """Read the 7-column wrdata layout: f, f, 0, Re(ig), Im(ig), Re(id), Im(id)."""
    rows = []
    with open(path) as fh:
        for line in fh:
            p = line.split()
            if len(p) != 7:
                continue
            try:
                v = [float(x) for x in p]
            except ValueError:
                continue
            rows.append((v[0], complex(v[3], v[4]), complex(v[5], v[6])))
    return rows


def _cross(rows, idx: int, target: float = 1.0):
    """First crossing of column idx through target, log-frequency interpolated."""
    for i in range(1, len(rows)):
        if rows[i - 1][idx] >= target > rows[i][idx]:
            f1, g1 = rows[i - 1][0], rows[i - 1][idx]
            f2, g2 = rows[i][0], rows[i][idx]
            return f1 * (f2 / f1) ** ((g1 - target) / (g1 - g2))
    return None


# --------------------------------------------------------------------------
# MOS f_T / f_MAX
# --------------------------------------------------------------------------
def mos_metrics(kind: str, vg: float, w: str = "100u", l: str = "1u",
                nf: int = 10, rg: str = "rshg=95", workdir: str = "/tmp"):
    """Return dict with fT, fMAX, gm, cgg for one bias point."""
    if kind == "n":
        net = f"""fT/fMAX
{INC}
Vd d 0 dc 5 ac 0
Vg g 0 dc {vg} ac 1
X1 d g 0 0 NMOS_nf w={w} l={l} nf={nf} {rg}
.ac dec 14 1Meg 100G
.control
set wr_singlescale
set wr_vecnames
run
wrdata r1.dat frequency i(vg) i(vd)
alter vg ac 0
alter vd ac 1
run
wrdata r2.dat frequency i(vg) i(vd)
.endc
.end
"""
    else:
        net = f"""fT/fMAX
{INC}
Vs s 0 dc 5 ac 0
Vd d 0 dc 0 ac 0
Vg g 0 dc {vg} ac 1
X1 d g s s PMOS_nf w={w} l={l} nf={nf} {rg}
.ac dec 14 1Meg 100G
.control
set wr_singlescale
set wr_vecnames
run
wrdata r1.dat frequency i(vg) i(vd)
alter vg ac 0
alter vd ac 1
run
wrdata r2.dat frequency i(vg) i(vd)
.endc
.end
"""
    _ngspice(net, workdir)
    a = _read_wrdata(os.path.join(workdir, "r1.dat"))
    b = _read_wrdata(os.path.join(workdir, "r2.dat"))

    rows = []
    for (f, i1, i2), (_, j1, j2) in zip(a, b):
        y11, y21, y12, y22 = -i1, -i2, -j1, -j2
        h21 = abs(y21 / y11)
        den = 4.0 * (y11.real * y22.real - (y12 * y21).real)
        U = abs(y21 - y12) ** 2 / den if den > 1e-30 else float("inf")
        rows.append((f, h21, U))

    y11 = -a[0][1]
    y21 = -a[0][2]
    gm = abs(y21)
    cgg = abs(y11) / (2 * math.pi * a[0][0])
    return {
        "fT_ghz": (_cross(rows, 1) or 0.0) / 1e9,
        "fMAX_ghz": (_cross(rows, 2) or 0.0) / 1e9,
        "gm_s": gm,
        "cgg_ff": cgg * 1e15,
    }


def mos_peak(kind: str, vgs, **kw):
    """Peak f_T and peak f_MAX over a Vgs list; the two peaks need not coincide."""
    best_ft = {"fT_ghz": 0.0}
    best_fmax = {"fMAX_ghz": 0.0}
    for vg in vgs:
        m = mos_metrics(kind, vg, **kw)
        if m["fT_ghz"] > best_ft["fT_ghz"]:
            best_ft = dict(m, vg=vg)
        if m["fMAX_ghz"] > best_fmax["fMAX_ghz"]:
            best_fmax = dict(m, vg=vg)
    return {"fT_peak": best_ft, "fMAX_peak": best_fmax}


# --------------------------------------------------------------------------
# Inductor one-port Q
# --------------------------------------------------------------------------
def _gen_inductor(turns: int, d_out: float, name: str, metal: str,
                  workdir: str) -> str:
    out = subprocess.run(
        [sys.executable, os.path.join(PDK, "flow/scripts/gen_inductor_model.py"),
         "--turns", str(turns), "--d-out", str(d_out), "--width", "8",
         "--spacing", "3", "--name", name, "--metal", metal],
        capture_output=True, text=True, check=True).stdout
    path = os.path.join(workdir, f"ind_{turns}.sp")
    with open(path, "w") as fh:
        fh.write(out)
    return path


def inductor_q(name: str, turns: int, d_out: float, term: str, metal: str,
               workdir: str = "/tmp"):
    """Return Q(f) and its sign crossings for one termination.

    term: 'short' (1 mohm), '50' (50 ohm) or 'open' (1 TOhm) at port 2.
    """
    os.makedirs(workdir, exist_ok=True)
    sub = _gen_inductor(turns, d_out, name, metal, workdir)
    r = {"short": "1e-3", "50": "50", "open": "1e12"}[term]
    net = f"""inductor Q
.include {MODELS}/models_IP62_inductor.lib
.include {sub}
V1 p 0 dc 0 ac 1
Rterm n 0 {r}
X1 p n 0 {name}
.ac dec 30 1Meg 100G
.control
run
let z = -1/i(v1)
let q = imag(z)/real(z)
print frequency q
.endc
.end
"""
    out = _ngspice(net, workdir)
    rows = []
    for line in out.splitlines():
        p = line.split()
        if len(p) >= 3 and p[0].isdigit():
            rows.append((float(p[1]), float(p[2])))

    crossings = []
    for i in range(1, len(rows)):
        f1, q1 = rows[i - 1]
        f2, q2 = rows[i]
        if (q1 > 0) != (q2 > 0):
            crossings.append(f1 * (f2 / f1) ** (q1 / (q1 - q2)))

    def at(f_target):
        return min(rows, key=lambda r: abs(math.log(r[0] / f_target)))[1]

    return {
        "q_100m": at(1e8),
        "q_1g": at(1e9),
        "q_10g": at(1e10),
        "crossings_ghz": [c / 1e9 for c in crossings],
    }


# --------------------------------------------------------------------------
def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--workdir", default="/tmp/opencode/rf_metrics")
    args = ap.parse_args(argv)
    wd = args.workdir

    result = {
        "nmos": mos_peak("n", [2.5, 3.0, 3.5, 4.0, 4.5, 5.0], workdir=wd),
        "pmos": mos_peak("p", [0.0, 0.5, 1.0, 1.5, 2.0, 2.5], workdir=wd),
    }
    # Intrinsic f_MAX at the same bias as the peak, so the only thing that
    # changes is Rg.
    for dev, kind in (("nmos", "n"), ("pmos", "p")):
        vg = result[dev]["fMAX_peak"]["vg"]
        intr = mos_metrics(kind, vg, rg="rgval=0.1", workdir=wd)
        result[dev]["fMAX_intrinsic_ghz"] = intr["fMAX_ghz"]
        result[dev]["fMAX_intrinsic_vg"] = vg
    # Rg must move f_MAX but not f_T.
    lo = mos_metrics("n", 4.0, rg="rgval=0.1", workdir=wd)
    hi = mos_metrics("n", 4.0, rg="rgval=792", workdir=wd)
    result["rg_sensitivity"] = {"fT_lo_ghz": lo["fT_ghz"], "fT_hi_ghz": hi["fT_ghz"],
                                "fMAX_lo_ghz": lo["fMAX_ghz"],
                                "fMAX_hi_ghz": hi["fMAX_ghz"]}

    for metal in ("al", "cu"):
        g = subprocess.run(
            [sys.executable, os.path.join(PDK, "flow/scripts/gen_inductor_model.py"),
             "--turns", "4", "--d-out", "250", "--width", "8", "--spacing", "3",
             "--name", "IND_4T_250U", "--metal", metal, "--format", "json"],
            capture_output=True, text=True, check=True).stdout
        d = json.loads(g)
        result[f"ind_4t_{metal}"] = {
            "r_dc_ohm": d["r_dc_ohm"],
            "r_dc_metal_ohm": d["r_dc_metal_ohm"],
            "q_metal_1g": d["q_metal_1ghz"],
            "rsh_m2": d["rsh_m2_ohm_sq"],
        }
        for term in ("short", "50", "open"):
            result[f"ind_4t_{metal}_{term}"] = inductor_q(
                "IND_4T_250U", 4, 250, term, metal, wd)

    for term in ("short", "50", "open"):
        result[f"ind_2t_al_{term}"] = inductor_q(
            "IND_2T_150U", 2, 150, term, "al", wd)

    if args.json:
        print(json.dumps(result, indent=2))
    else:
        for dev in ("nmos", "pmos"):
            ft = result[dev]["fT_peak"]
            fm = result[dev]["fMAX_peak"]
            print("%s: fT peak %.2f GHz @Vg=%.2f (gm=%.3e S, Cgg=%.1f fF); "
                  "fMAX peak %.2f GHz @Vg=%.2f (intrinsic %.2f GHz at Rg=0.1)"
                  % (dev.upper(), ft["fT_ghz"], ft["vg"], ft["gm_s"],
                     ft["cgg_ff"], fm["fMAX_ghz"], fm["vg"],
                     result[dev]["fMAX_intrinsic_ghz"]))
        rs = result["rg_sensitivity"]
        print("Rg 0.1 -> 792 ohm: fT %.2f -> %.2f GHz (%.1f %%), "
              "fMAX %.2f -> %.2f GHz"
              % (rs["fT_lo_ghz"], rs["fT_hi_ghz"],
                 100 * (rs["fT_hi_ghz"] / rs["fT_lo_ghz"] - 1),
                 rs["fMAX_lo_ghz"], rs["fMAX_hi_ghz"]))
        for metal in ("al", "cu"):
            d = result[f"ind_4t_{metal}"]
            print("4T %s: Rdc=%.2f ohm Rsh_M2=%.4f Qmetal(1G)=%.3f"
                  % (metal.upper(), d["r_dc_ohm"], d["rsh_m2"], d["q_metal_1g"]))
        for key in sorted(k for k in result
                          if k.startswith("ind_") and "q_100m" in result[k]):
            q = result[key]
            print("%-18s Q(.1G)=%7.3f Q(1G)=%7.3f Q(10G)=%7.3f  crossings(GHz)=%s"
                  % (key, q["q_100m"], q["q_1g"], q["q_10g"],
                     ", ".join("%.2f" % c for c in q["crossings_ghz"]) or "-"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
