#!/usr/bin/env python3
"""Reproduce the upstream TR-1um C4004 route-guide flow for TR10_cmp_sc.

The upstream OpenROAD sign-off (jun1okamura/TR-1um_C4004 ``openroad/``)
routes the 59.4 um compact cells by *not* asking TritonRoute to touch the
cell interior:

* a dedicated global-route cell LEF keeps every signal pin on M1 so
  ``global_route`` allocates M1 guides across the rows
  (``TR10_cmp_sc_grt.lef``);
* the detail-route LEF keeps the same pins on M2 only plus a full-cell
  M1/V1 OBS (``TR10_cmp_sc.lef``);
* the global-route guides are inflated by one channel width so detail
  routing may wander off the global topology into the free channels.

This script is stage 1+2 of that flow: it runs ``global_route`` against a
placed DEF using the M1-pin LEF, then expands every guide rectangle.
Run it after ``librelane --to OpenROAD.DetailedPlacement`` (or any step
that still carries the final placement in its DEF view) and before
``librelane --from OpenROAD.DetailedRouting``.  The patched
``scripts/openroad/drt.tcl`` picks the expanded guide back up via
``read_guides``.

Usage:
    tr1um_route_guide.py --def placement.def --out expanded.guide \
        [--pad-um 81] [--openroad /path/to/openroad]
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CMP = ROOT / "libs.ref/TR10_cmp_sc"
TECHLEF = CMP / "techlef/TR10_tech.tlef"
GRT_LEF = CMP / "lef/TR10_cmp_sc_grt.lef"
DRT_LEF = CMP / "lef/TR10_cmp_sc.lef"

GRT_TCL = """\
read_lef {techlef}
read_lef {grt_lef}
read_def {def_path}
set_routing_layers -signal M1-M2
global_route -guide_file {guide} -congestion_iterations 50 -allow_congestion -verbose
puts "TR1UM_GRT_DONE"
"""


def expand_guide(src: Path, dst: Path, pad_dbu: int, max_xy: tuple[int, int]) -> int:
    """Inflate every guide rectangle by ``pad_dbu`` (clamped to the die)."""
    rect = re.compile(r"^(\d+)\s+(\d+)\s+(\d+)\s+(\d+)\s+([A-Za-z0-9_]+)\s*$")
    out: list[str] = []
    for line in src.read_text().splitlines():
        m = rect.match(line.strip())
        if not m:
            out.append(line)
            continue
        x1, y1, x2, y2 = (int(m.group(i)) for i in range(1, 5))
        layer = m.group(5)
        out.append(
            f"{max(0, x1 - pad_dbu)} {max(0, y1 - pad_dbu)} "
            f"{min(max_xy[0], x2 + pad_dbu)} {min(max_xy[1], y2 + pad_dbu)} {layer}"
        )
    dst.write_text("\n".join(out) + "\n")
    return len(out)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--def", dest="def_path", required=True, type=Path,
                    help="placed DEF (e.g. runs/.../33-openroad-detailedplacement/*.def)")
    ap.add_argument("--out", required=True, type=Path, help="expanded guide output")
    ap.add_argument("--pad-um", type=float, default=81.0,
                    help="guide expansion per side, um (upstream uses 81)")
    ap.add_argument("--openroad", default="openroad", help="openroad binary")
    ap.add_argument("--die", default=None,
                    help="die WxH in um for clamping, e.g. 1000x1200 (default: read from DEF)")
    args = ap.parse_args()

    def_path = args.def_path.resolve()
    if not def_path.is_file():
        sys.exit(f"DEF not found: {def_path}")

    # Default die box = the DEF DIEAREA, in dbu (1000/um).
    die = (1 << 62, 1 << 62)
    if args.die:
        w, h = args.die.lower().split("x")
        die = (int(float(w) * 1000), int(float(h) * 1000))
    else:
        m = re.search(r"DIEAREA\s*\([^)]*?\)\s*\(\s*(\d+)\s+(\d+)\s*\)", def_path.read_text())
        if m:
            die = (int(m.group(1)), int(m.group(2)))

    with tempfile.TemporaryDirectory(prefix="tr1um_grt_") as td:
        td = Path(td)
        guide = td / "route.guide"
        tcl = td / "grt.tcl"
        tcl.write_text(GRT_TCL.format(
            techlef=TECHLEF, grt_lef=GRT_LEF, def_path=def_path, guide=guide))
        proc = subprocess.run(
            [args.openroad, "-exit", "-no_splash", str(tcl)],
            capture_output=True, text=True)
        log = proc.stdout + proc.stderr
        if "TR1UM_GRT_DONE" not in log or not guide.is_file():
            sys.stderr.write(log[-8000:])
            sys.exit("global_route did not produce a guide")

        n = expand_guide(guide, args.out, int(round(args.pad_um * 1000)), die)
        m1 = sum(1 for l in args.out.read_text().splitlines() if l.rstrip().endswith(" M1"))
        m2 = sum(1 for l in args.out.read_text().splitlines() if l.rstrip().endswith(" M2"))
        print(f"expanded guide -> {args.out} ({n} rects; M1={m1} M2={m2}, pad={args.pad_um}um)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
