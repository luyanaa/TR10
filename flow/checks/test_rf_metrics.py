#!/usr/bin/env python3
"""Regression gate for the RF figures of merit.

Runs flow/scripts/rf_metrics.py and checks the physics, not a frozen copy of
the model:

  * f_T is independent of gate resistance, f_MAX is not;
  * f_MAX < f_T is NOT required (it is false for a low-Rg finger), but f_MAX
    must fall when Rg rises and must stay below the intrinsic limit;
  * the Al / Cu Rdc ratio must be the conductivity ratio 58/35;
  * the one-port inductor Q must change sign exactly where the input stops
    being inductive: open-port 4T never, 50-ohm 4T below ~8.7 GHz, and the
    small 2T only above ~1 GHz.

Exit 0 when every check passes, 1 otherwise.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
PDK = os.path.abspath(os.path.join(HERE, "..", ".."))
SCRIPT = os.path.join(PDK, "flow/scripts/rf_metrics.py")

PASS = 0
FAIL = 0


def ok(name):
    global PASS
    PASS += 1
    print("PASS  %s" % name)


def bad(name, detail=""):
    global FAIL
    FAIL += 1
    print("FAIL  %s%s" % (name, (": " + detail) if detail else ""))


def between(name, value, lo, hi):
    if lo <= value <= hi:
        ok("%s (%.4g in [%.4g, %.4g])" % (name, value, lo, hi))
    else:
        bad(name, "%.4g outside [%.4g, %.4g]" % (value, lo, hi))


def main() -> int:
    out = subprocess.run([sys.executable, SCRIPT, "--json"],
                         capture_output=True, text=True)
    if out.returncode != 0:
        print(out.stdout)
        print(out.stderr, file=sys.stderr)
        print("FAIL  rf_metrics.py did not run")
        return 1
    r = json.loads(out.stdout)

    # ---- MOS ------------------------------------------------------------
    n_ft = r["nmos"]["fT_peak"]["fT_ghz"]
    n_fm = r["nmos"]["fMAX_peak"]["fMAX_ghz"]
    p_ft = r["pmos"]["fT_peak"]["fT_ghz"]
    p_fm = r["pmos"]["fMAX_peak"]["fMAX_ghz"]
    between("NMOS fT peak", n_ft, 2.4, 2.9)
    between("NMOS fMAX peak (Rg=7.9 ohm)", n_fm, 4.0, 5.0)
    between("PMOS fT peak", p_ft, 1.0, 1.35)
    between("PMOS fMAX peak (Rg=7.9 ohm)", p_fm, 1.8, 2.4)
    if p_fm < p_ft:
        bad("PMOS fMAX > fT", "%.3f < %.3f" % (p_fm, p_ft))
    else:
        ok("PMOS fMAX > fT (low-Rg finger)")

    for dev in ("nmos", "pmos"):
        peak = r[dev]["fMAX_peak"]["fMAX_ghz"]
        intr = r[dev]["fMAX_intrinsic_ghz"]
        if intr > peak:
            ok("%s fMAX improves when Rg drops (%.2f -> %.2f GHz)"
               % (dev.upper(), peak, intr))
        else:
            bad("%s intrinsic fMAX" % dev.upper(), "%.2f <= %.2f" % (intr, peak))

    rs = r["rg_sensitivity"]
    drift = abs(rs["fT_hi_ghz"] / rs["fT_lo_ghz"] - 1.0)
    if drift < 0.02:
        ok("fT is independent of Rg (%.2f %% drift)" % (100 * drift))
    else:
        bad("fT is independent of Rg", "%.2f %% drift" % (100 * drift))
    if rs["fMAX_lo_ghz"] > 4.5 and rs["fMAX_hi_ghz"] < 1.2:
        ok("fMAX falls with Rg (%.2f -> %.2f GHz)"
           % (rs["fMAX_lo_ghz"], rs["fMAX_hi_ghz"]))
    else:
        bad("fMAX falls with Rg", "%.2f -> %.2f GHz"
            % (rs["fMAX_lo_ghz"], rs["fMAX_hi_ghz"]))

    # ---- Al vs Cu -------------------------------------------------------
    al = r["ind_4t_al"]
    cu = r["ind_4t_cu"]
    # r_dc_ohm includes the metal-independent via resistance, so compare the
    # metal part only: it must scale exactly with 58/35.
    ratio = al["r_dc_metal_ohm"] / cu["r_dc_metal_ohm"]
    if abs(ratio - 58.0 / 35.0) < 1e-6:
        ok("Al/Cu metal Rdc ratio == 58/35 (%.6f)" % ratio)
    else:
        bad("Al/Cu metal Rdc ratio", "%.6f != %.6f" % (ratio, 58.0 / 35.0))
    if al["q_metal_1g"] > 0:
        ok("series/metal Q is positive at 1 GHz (%.3f)" % al["q_metal_1g"])
    else:
        bad("series/metal Q is positive at 1 GHz")

    # ---- inductor one-port Q -------------------------------------------
    q = r["ind_4t_al_open"]
    if q["q_1g"] < 0 and not q["crossings_ghz"]:
        ok("4T open-port Q is negative over the whole band")
    else:
        bad("4T open-port Q", "Q(1G)=%.3f crossings=%s"
            % (q["q_1g"], q["crossings_ghz"]))

    q = r["ind_4t_al_50"]
    if q["q_1g"] > 0 > q["q_10g"] and len(q["crossings_ghz"]) == 1:
        between("4T 50-ohm Q sign change", q["crossings_ghz"][0], 8.0, 9.2)
    else:
        bad("4T 50-ohm Q sign change",
            "Q(1G)=%.3f Q(10G)=%.3f crossings=%s"
            % (q["q_1g"], q["q_10g"], q["crossings_ghz"]))

    q = r["ind_4t_al_short"]
    if q["q_1g"] > 0 and q["crossings_ghz"]:
        between("4T shorted-port Q sign change", q["crossings_ghz"][0], 8.0, 9.2)
    else:
        bad("4T shorted-port Q sign change", "Q(1G)=%.3f" % q["q_1g"])

    q = r["ind_2t_al_50"]
    if q["q_1g"] < 0 < q["q_10g"] and len(q["crossings_ghz"]) == 2:
        between("2T 50-ohm lower Q crossing", q["crossings_ghz"][0], 0.8, 1.3)
        between("2T 50-ohm upper Q crossing", q["crossings_ghz"][1], 18.0, 23.0)
    else:
        bad("2T 50-ohm Q windows",
            "Q(1G)=%.3f Q(10G)=%.3f crossings=%s"
            % (q["q_1g"], q["q_10g"], q["crossings_ghz"]))

    q = r["ind_2t_al_open"]
    if q["q_1g"] < 0 and len(q["crossings_ghz"]) == 2:
        between("2T open-port first crossing", q["crossings_ghz"][0], 19.0, 24.0)
        between("2T open-port second crossing", q["crossings_ghz"][1], 26.0, 32.0)
    else:
        bad("2T open-port Q window", "Q(1G)=%.3f crossings=%s"
            % (q["q_1g"], q["crossings_ghz"]))

    # ---- Al must not move the sign boundary ----------------------------
    a = r["ind_4t_al_50"]["crossings_ghz"][0]
    c = r["ind_4t_cu_50"]["crossings_ghz"][0]
    if abs(a / c - 1.0) < 0.02:
        ok("Al vs Cu moves the 50-ohm sign boundary by < 2 %% (%.2f / %.2f GHz)"
           % (a, c))
    else:
        bad("Al vs Cu sign boundary", "%.2f vs %.2f GHz" % (a, c))

    print("-" * 50)
    print("PASS %d  FAIL %d" % (PASS, FAIL))
    return 0 if FAIL == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
