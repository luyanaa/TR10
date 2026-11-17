#!/usr/bin/env python3
"""TR10 direct-conversion I/Q receiver example regression.

Runs the ngspice testbenches under examples/rf_iq_receiver/spice and checks
the block- and system-level metrics against the values in DESIGN.md:

  LNA          19.9 dB at 1 MHz, 50 ohm input, 54 kHz loaded bandwidth
  LNA AGC      monotonic 0.47 -> 9.9 V/V over agc = 0..5 V
  LNA bands    0.1 / 1 / 10 / 100 MHz tank scaling (>18 dB up to 10 MHz)
  mixer+TIA    1 mV RF, m=0.5 -> >2 mVpp baseband envelope, clean 3 kHz
  AM demod     25 mV envelope -> >300 mV audio, <5 % 2nd/3rd harmonic
  SSB demod    10 mV I/Q at 3 kHz -> >150 mV selected, >30 dB rejection
  FM demod     100 mV I/Q, 75 kHz deviation -> >30 mV audio at 3 kHz
  LO gen       4 phases, 25 % duty, non-overlapping (behavioral)
  LO divider   VCO/2 clock -> 4 phases at f_lo, 22-29 % duty
  PFD          UP/DN vs phase: +/-90 deg -> 1.25 of 5 V, 0 deg -> reset only
  PFD freq     UP for a slow FB, DN for a fast FB (frequency steering)
  full AM      LNA -> ... -> audio, >100 mV audio at 3 kHz (--full)

Usage:
    python3 examples/rf_iq_receiver/scripts/run_cases.py
    python3 examples/rf_iq_receiver/scripts/run_cases.py --full
    python3 examples/rf_iq_receiver/scripts/run_cases.py --json
"""
from __future__ import annotations

import argparse
import json
import math
import os
import re
import shutil
import subprocess
import sys
import tempfile

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
PKG = os.path.abspath(os.path.join(HERE, ".."))
PDK = os.path.abspath(os.path.join(PKG, "..", ".."))
SPICE = os.path.join(PKG, "spice")


def run_ngspice(netlist: str, workdir: str, timeout: int = 900) -> str:
    """Run a netlist in workdir; return stdout.  Raises on ngspice failure."""
    path = os.path.join(SPICE, netlist)
    # ngspice links libgomp; its default spin-wait threads thrash on a loaded
    # machine (a 10 us transient went from 23 s to 0.3 s with PASSIVE).
    env = dict(os.environ)
    env.setdefault("OMP_WAIT_POLICY", "PASSIVE")
    proc = subprocess.run(
        ["ngspice", "-b", path],
        cwd=workdir,
        capture_output=True,
        text=True,
        timeout=timeout,
        env=env,
    )
    out = proc.stdout + proc.stderr
    with open(os.path.join(workdir, netlist + ".log"), "w") as fh:
        fh.write(out)
    if proc.returncode != 0:
        raise RuntimeError(f"{netlist} exited {proc.returncode}\n{out[-2000:]}")
    return out


def load_wrdata(path: str) -> np.ndarray:
    return np.loadtxt(path, skiprows=1)


def tone_amp(t: np.ndarray, x: np.ndarray, f: float) -> float:
    """Least-squares amplitude of a sinusoid at f, with a DC term."""
    w = 2.0 * math.pi * f
    A = np.column_stack([np.sin(w * t), np.cos(w * t), np.ones_like(t)])
    coef, *_ = np.linalg.lstsq(A, x, rcond=None)
    return float(math.hypot(coef[0], coef[1]))


def thd(t: np.ndarray, x: np.ndarray, f: float, harmonics=(2, 3)) -> float:
    fund = tone_amp(t, x, f)
    if fund <= 0:
        return float("inf")
    return math.sqrt(sum(tone_amp(t, x, f * h) ** 2 for h in harmonics)) / fund


class Checker:
    def __init__(self) -> None:
        self.results = []

    def check(self, name: str, ok: bool, detail: str) -> None:
        self.results.append({"name": name, "ok": bool(ok), "detail": detail})
        print(f"{'PASS' if ok else 'FAIL'}  {name}")
        print(f"      {detail}")

    def done(self, as_json: bool) -> int:
        npass = sum(r["ok"] for r in self.results)
        nfail = len(self.results) - npass
        print("\n----------------------------------------")
        print(f"PASS {npass}  FAIL {nfail}")
        if as_json:
            print(json.dumps({"pass": npass, "fail": nfail,
                              "results": self.results}, indent=2))
        return 0 if nfail == 0 else 1


def case_lna(ck: Checker, work: str) -> None:
    run_ngspice("test_lna.sp", work)
    d = load_wrdata(os.path.join(work, "lna_ac.dat"))
    f = d[:, 0]
    g = np.abs((d[:, 1] + 1j * d[:, 2]) / (d[:, 3] + 1j * d[:, 4]))
    i = int(np.argmin(np.abs(np.log(f / 1e6))))
    g0 = float(g[i])
    gain_db = 20.0 * math.log10(g0)
    ck.check("LNA gain at 1 MHz", 18.5 <= gain_db <= 21.5,
             f"{gain_db:.2f} dB ({g0:.3f} V/V), target 19.9 +/- 1.5 dB")

    th = g0 / math.sqrt(2.0)
    lo = hi = None
    for k in range(len(f) - 1):
        if g[k] < th <= g[k + 1]:
            lo = f[k] * (f[k + 1] / f[k]) ** ((th - g[k]) / (g[k + 1] - g[k]))
        if g[k] >= th > g[k + 1]:
            hi = f[k] * (f[k + 1] / f[k]) ** ((g[k] - th) / (g[k] - g[k + 1]))
    bw = (hi - lo) if lo and hi else float("nan")
    ck.check("LNA loaded -3 dB bandwidth", 40e3 <= bw <= 70e3,
             f"{bw/1e3:.1f} kHz, target 50-55 kHz (Q=20 tank)")


def case_lna_bands(ck: Checker, work: str) -> None:
    run_ngspice("test_lna_bands.sp", work)
    d = load_wrdata(os.path.join(work, "lna_bands.dat"))
    f = d[:, 0]
    got = []
    for k, f0 in enumerate((100e3, 1e6, 10e6, 100e6)):
        g = d[:, 1 + k]
        i = int(np.argmin(np.abs(np.log(f / f0))))
        got.append(20.0 * math.log10(float(g[i])))
    ck.check("LNA band scaling 0.1/1/10 MHz", all(g >= 18.0 for g in got[:3]),
             ", ".join(f"{x:.1f} dB" for x in got[:3]) + ", target > 18 dB")
    ck.check("LNA at 100 MHz", got[3] >= 8.0,
             f"{got[3]:.1f} dB at 100 MHz (tank detuned by device capacitance), target > 8 dB")


def case_lna_agc(ck: Checker, work: str) -> None:
    out = run_ngspice("test_lna_agc.sp", work)
    rows = re.findall(r"^agc=([0-9.]+)\s+gain=([0-9.eE+-]+)", out, re.M)
    gains = [(float(a), float(g)) for a, g in rows]
    ck.check("LNA AGC sweep present", len(gains) >= 8,
             f"{len(gains)} points")
    if not gains:
        return
    mono = all(gains[k][1] <= gains[k + 1][1] + 1e-6 for k in range(len(gains) - 1))
    ck.check("LNA AGC monotonic", mono,
             "gain rises with agc: " + ", ".join(f"{g:.2f}" for _, g in gains))
    ck.check("LNA AGC low end", 0.35 <= gains[0][1] <= 0.65,
             f"agc=0 -> {gains[0][1]:.3f} V/V, target 0.47")
    ck.check("LNA AGC high end", 9.0 <= gains[-1][1] <= 11.0,
             f"agc=5 -> {gains[-1][1]:.3f} V/V, target 9.9")


def case_mixer_tia(ck: Checker, work: str) -> None:
    run_ngspice("test_mixer_tia.sp", work)
    d = load_wrdata(os.path.join(work, "mixer_tia.dat"))
    t, i, q = d[:, 0], d[:, 1], d[:, 2]
    # one exact 3 kHz period at the end of the run
    T = 1.0 / 3e3
    m = (t >= t[-1] - T) & (t <= t[-1])
    ai = tone_amp(t[m], i[m], 3e3)
    aq = tone_amp(t[m], q[m], 3e3)
    h2i = tone_amp(t[m], i[m], 6e3)
    ck.check("mixer+TIA 3 kHz envelope", 2e-3 <= ai <= 5e-3,
             f"I = {ai*1e3:.2f} mV, Q = {aq*1e3:.2f} mV, target 2-4 mV")
    ck.check("mixer+TIA envelope is clean", h2i <= 0.10 * ai,
             f"6 kHz / 3 kHz = {100*h2i/ai if ai else float('nan'):.1f} %, target < 10 %")


def case_demod_am(ck: Checker, work: str) -> None:
    run_ngspice("test_demod_am.sp", work)
    d = load_wrdata(os.path.join(work, "demod_am.dat"))
    t, v = d[:, 0], d[:, 1]
    T = 1.0 / 3e3
    m = (t >= t[-1] - T) & (t <= t[-1])
    a = tone_amp(t[m], v[m], 3e3)
    ck.check("AM demod audio amplitude", a >= 0.30,
             f"{a*1e3:.1f} mV at 3 kHz from a 25 mV envelope, target > 300 mV")
    d3 = thd(t[m], v[m], 3e3, harmonics=(2, 3))
    ck.check("AM demod 2nd/3rd harmonic", d3 <= 0.05,
             f"THD(2,3) = {100*d3:.2f} %, target < 5 %")


def case_demod_ssb(ck: Checker, work: str) -> None:
    run_ngspice("test_demod_ssb.sp", work)
    d = load_wrdata(os.path.join(work, "demod_ssb.dat"))
    t = d[:, 0]
    m = (t >= 2e-3) & (t <= 3e-3)
    usb = tone_amp(t[m], d[m, 1], 3e3)
    lsb = tone_amp(t[m], d[m, 2], 3e3)
    ck.check("SSB selected sideband", lsb >= 0.15,
             f"LSB (Q=-sin) = {lsb*1e3:.1f} mV from 10 mV I/Q, target > 150 mV")
    rej = 20.0 * math.log10(lsb / usb) if usb > 0 else float("inf")
    ck.check("SSB sideband rejection", rej >= 30.0,
             f"USB = {usb*1e3:.2f} mV, rejection = {rej:.1f} dB, target > 30 dB")


def case_demod_fm(ck: Checker, work: str) -> None:
    run_ngspice("test_demod_fm.sp", work)
    d = load_wrdata(os.path.join(work, "demod_fm.dat"))
    t = d[:, 0]
    m = (t >= 2e-3) & (t <= 3e-3)
    a = tone_amp(t[m], d[m, 1], 3e3)
    ck.check("FM demod audio amplitude", a >= 0.030,
             f"{a*1e3:.1f} mV at 3 kHz from 100 mV I/Q at 75 kHz deviation, target > 30 mV")
    d3 = thd(t[m], d[m, 1], 3e3, harmonics=(2, 3))
    ck.check("FM demod distortion", d3 <= 0.05,
             f"THD(2,3) = {100*d3:.2f} %, target < 5 %")


def case_lo_gen(ck: Checker, work: str) -> None:
    run_ngspice("test_lo_gen.sp", work)
    d = load_wrdata(os.path.join(work, "lo_gen.dat"))
    t = d[:, 0]
    m = t >= 2e-6
    duties = [(d[m, k + 1] > 2.5).mean() for k in range(4)]
    ck.check("LO 25 % duty phases",
             all(0.22 <= x <= 0.28 for x in duties),
             ", ".join(f"{x*100:.1f} %" for x in duties) + ", target 25 % each")
    overlap = sum((d[m, k + 1] > 2.5).astype(int) for k in range(4))
    ck.check("LO phases non-overlapping", overlap.max() == 1,
             f"max simultaneous high phases = {int(overlap.max())}, target 1")


def case_lo_div(ck: Checker, work: str) -> None:
    run_ngspice("test_lo_div.sp", work)
    d = load_wrdata(os.path.join(work, "lo_div.dat"))
    t = d[:, 0]
    m = t >= 6e-6
    duties = [(d[m, k + 1] > 2.5).mean() for k in range(4)]
    ck.check("divider 4 phases at f_lo",
             all(0.22 <= x <= 0.29 for x in duties),
             ", ".join(f"{x*100:.1f} %" for x in duties) + ", target 25 % +/- 4 %")
    # each phase must toggle at half the 2 MHz clock -> 1 us period
    x = d[:, 1]
    hi = x > 2.5
    idx = np.where((~hi[:-1]) & hi[1:])[0]
    per = (t[idx[-1]] - t[idx[0]]) / (len(idx) - 1) if len(idx) > 2 else 0.0
    ck.check("divider is divide-by-2", abs(per - 1e-6) <= 0.05e-6,
             f"period = {per*1e6:.3f} us, target 1.000 us (2 MHz clock / 2)")


def case_pfd(ck: Checker, work: str) -> None:
    out = run_ngspice("test_pfd.sp", work)
    rows = {}
    for line in out.splitlines():
        if line.startswith("ph="):
            parts = dict(p.split("=") for p in line.split())
            rows[float(parts["ph"])] = (float(parts["up"]), float(parts["dn"]))
    ok_shape = 90.0 in rows and -90.0 in rows and 0.0 in rows
    ck.check("PFD phase characteristic present", ok_shape,
             f"{len(rows)} phase points")
    if not ok_shape:
        return
    up90, dn90 = rows[90.0]
    upm90, dnm90 = rows[-90.0]
    ck.check("PFD +90 deg drives UP", 1.05 <= up90 <= 1.55,
             f"UP = {up90:.3f}, target 1.25 (90 deg of 5 V)")
    ck.check("PFD -90 deg drives DN", 1.05 <= dnm90 <= 1.55,
             f"DN = {dnm90:.3f}, target 1.25")
    up0, dn0 = rows[0.0]
    ck.check("PFD zero phase is balanced", up0 <= 0.20 and dn0 <= 0.20,
             f"UP = {up0:.3f}, DN = {dn0:.3f}, target < 0.20 each")


def case_pfd_freq(ck: Checker, work: str) -> None:
    out = run_ngspice("test_pfd_freq.sp", work)
    rows = {}
    for line in out.splitlines():
        if line.startswith("ffb="):
            parts = dict(p.split("=") for p in line.split())
            rows[parts["ffb"]] = (float(parts["up"]), float(parts["dn"]))
    ck.check("PFD frequency sweep present", len(rows) >= 3, f"{len(rows)} points")
    if len(rows) < 3:
        return
    slow = rows.get("0.995meg")
    fast = rows.get("1.005meg")
    ck.check("PFD steers a slow feedback up", slow is not None and slow[0] > slow[1],
             f"0.995 MHz: UP = {slow[0]:.3f}, DN = {slow[1]:.3f}" if slow else "missing")
    ck.check("PFD steers a fast feedback down", fast is not None and fast[1] > fast[0],
             f"1.005 MHz: UP = {fast[0]:.3f}, DN = {fast[1]:.3f}" if fast else "missing")


def case_full_am(ck: Checker, work: str) -> None:
    run_ngspice("tb_am_1m.sp", work)
    d = load_wrdata(os.path.join(work, "tb_am_1m.dat"))
    t, audio = d[:, 0], d[:, 1]
    T = 1.0 / 3e3
    m = (t >= t[-1] - T) & (t <= t[-1])
    a = tone_amp(t[m], audio[m], 3e3)
    ck.check("full AM chain audio", a >= 0.10,
             f"{a*1e3:.1f} mV at 3 kHz from a 1 mV RF input, target > 100 mV")
    d3 = thd(t[m], audio[m], 3e3, harmonics=(2, 3))
    ck.check("full AM chain distortion", d3 <= 0.10,
             f"THD(2,3) = {100*d3:.2f} %, target < 10 %")


def case_full_am_pex(ck: Checker, work: str) -> None:
    """The same end-to-end AM chain with the post-layout modules
    (pre-layout devices + Magic PEX caps; see gen_post_am.py)."""
    subprocess.run([sys.executable, os.path.join(HERE, "gen_post_am.py")],
                   check=True, capture_output=True, text=True)
    run_ngspice("tb_am_1m_post.sp", work)
    d = load_wrdata(os.path.join(work, "tb_am_1m_post.dat"))
    t, audio = d[:, 0], d[:, 1]
    T = 1.0 / 3e3
    m = (t >= t[-1] - T) & (t <= t[-1])
    a = tone_amp(t[m], audio[m], 3e3)
    ck.check("full AM chain audio (post-layout)", a >= 0.10,
             f"{a*1e3:.1f} mV at 3 kHz from a 1 mV RF input, target > 100 mV")
    d3 = thd(t[m], audio[m], 3e3, harmonics=(2, 3))
    ck.check("full AM chain distortion (post-layout)", d3 <= 0.10,
             f"THD(2,3) = {100*d3:.2f} %, target < 10 %")


def osc_freq(path: str, t_lo: float = 2e-6, t_hi: float = 5e-6):
    """Frequency, swing and crossings of a differential VCO node."""
    d = load_wrdata(path)
    t, x = d[:, 0], d[:, 1]
    m = (t >= t_lo) & (t <= t_hi)
    t2, x2 = t[m], x[m] - x[m].mean()
    z = np.where(np.diff(np.signbit(x2)))[0]

    def cross(i):
        t0, t1 = t2[i], t2[i + 1]
        y0, y1 = x2[i], x2[i + 1]
        return t0 - y0 * (t1 - t0) / (y1 - y0)

    tc = [cross(i) for i in z]
    half = (tc[-1] - tc[0]) / (len(tc) - 1)
    return 1.0 / (2 * half), x2.max() - x2.min(), len(tc)


def case_vco_pex(ck: Checker, work: str) -> None:
    """Free-running VCO with the extracted tank parasitics."""
    subprocess.run([sys.executable, os.path.join(HERE, "gen_post_am.py")],
                   check=True, capture_output=True, text=True)
    run_ngspice("tb_vco_post.sp", work)
    f, swing, n = osc_freq(os.path.join(work, "vco_post.dat"))
    ck.check("VCO oscillates post-layout", n >= 8 and swing > 0.5,
             f"{f/1e6:.4f} MHz, {swing:.3f} Vpp, {n} crossings in 3 us")
    ck.check("VCO frequency shift post-layout", abs(f - 2e6) / 2e6 <= 0.02,
             f"{f/1e6:.4f} MHz vs 2.000 MHz design, "
             f"{100*(f-2e6)/2e6:+.2f} % (tank +2.66 pF of varactor diffusion)")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--full", action="store_true",
                    help="also run the 1 MHz end-to-end AM transient")
    ap.add_argument("--json", action="store_true", help="print a JSON summary")
    ap.add_argument("--keep", action="store_true", help="keep the work directory")
    args = ap.parse_args()

    work = tempfile.mkdtemp(prefix="rx_cases_")
    ck = Checker()
    try:
        print("== LNA ==")
        case_lna(ck, work)
        print("\n== LNA AGC ==")
        case_lna_agc(ck, work)
        print("\n== LNA band scaling ==")
        case_lna_bands(ck, work)
        print("\n== mixer + TIA ==")
        case_mixer_tia(ck, work)
        print("\n== AM demodulator ==")
        case_demod_am(ck, work)
        print("\n== SSB demodulator ==")
        case_demod_ssb(ck, work)
        print("\n== FM demodulator ==")
        case_demod_fm(ck, work)
        print("\n== LO generator ==")
        case_lo_gen(ck, work)
        print("\n== LO divider ==")
        case_lo_div(ck, work)
        print("\n== PFD ==")
        case_pfd(ck, work)
        print("\n== PFD frequency steering ==")
        case_pfd_freq(ck, work)
        if args.full:
            print("\n== full AM chain at 1 MHz ==")
            case_full_am(ck, work)
            if os.path.isdir(os.path.join(PKG, "layout", "pex")) and \
                    os.path.exists(os.path.join(PKG, "layout", "pex", "rx_amdemod.spice")):
                print("\n== full AM chain at 1 MHz (post-layout) ==")
                case_full_am_pex(ck, work)
                print("\n== VCO free running (post-layout) ==")
                case_vco_pex(ck, work)
            else:
                print("\nSKIP  full AM chain post-layout "
                      "(run layout/run_signoff.sh first)")
        else:
            print("\nSKIP  full AM chain (use --full)")
        rc = ck.done(args.json)
    finally:
        if args.keep:
            print(f"work directory: {work}")
        else:
            shutil.rmtree(work, ignore_errors=True)
    return rc


if __name__ == "__main__":
    sys.exit(main())
