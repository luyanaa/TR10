#!/usr/bin/env python3
"""T0/T1/T2/T3 PDN signal-integrity gate.

Checks from DEF + LEF:
  * PDN M1/M2 metal vs signal pin metal -> electrical_short
  * PDN M1/M2 metal vs LEF OBS -> routing_obstruction
  * PDN VDD shape vs PDN GND shape -> pg_pg_short
  * every cell VDD/GND pin has matching PDN coverage -> pg_pin_unconnected

It does not replace GDS extraction/LVS.
"""

import argparse
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import pdn_experiment_postcheck as pc


def parse_lef(path):
    text = Path(path).read_text()
    parts = re.split(r"(?m)^MACRO\s+(\S+)\s*$", text)
    macros = {}
    for i in range(1, len(parts), 2):
        name = parts[i]
        block = parts[i + 1]
        m = re.search(r"SIZE\s+([\d.]+)\s+BY\s+([\d.]+)", block)
        if not m:
            continue
        width, height = float(m.group(1)), float(m.group(2))
        ctx = None
        layer = None
        rects = []
        for line in block.splitlines():
            s = line.strip()
            p = re.match(r"PIN\s+(\S+)", s)
            if p:
                ctx = p.group(1)
                layer = None
                continue
            if s.startswith("OBS"):
                ctx = "OBS"
                layer = None
                continue
            l = re.match(r"LAYER\s+(\S+)", s)
            if l:
                layer = l.group(1)
                continue
            r = re.match(r"RECT\s+([-\d.]+)\s+([-\d.]+)\s+([-\d.]+)\s+([-\d.]+)", s)
            if r and layer in ("M1", "M2") and ctx is not None:
                rects.append((ctx, layer, tuple(float(r.group(j)) for j in range(1, 5))))
        macros[name] = {"width": width, "height": height, "rects": rects}
    return macros


def parse_components(def_text):
    comps = []
    for line in def_text.splitlines():
        m = re.match(r"\s*-\s+(\S+)\s+(\S+)\s+\+\s+PLACED\s+\(\s*(-?\d+)\s+(-?\d+)\s*\)\s+(\S+)", line)
        if m:
            comps.append({
                "name": m.group(1), "cell": m.group(2),
                "x": int(m.group(3)) / pc.UNITS,
                "y": int(m.group(4)) / pc.UNITS,
                "orient": m.group(5),
            })
    return comps


def transform(rect, comp, cell):
    x1, y1, x2, y2 = rect
    w = cell["width"]
    h = cell["height"]
    o = comp["orient"]
    if o == "N":
        return (comp["x"] + x1, comp["y"] + y1, comp["x"] + x2, comp["y"] + y2)
    if o == "S":
        return (comp["x"] + w - x2, comp["y"] + h - y2,
                comp["x"] + w - x1, comp["y"] + h - y1)
    if o == "FS":
        return (comp["x"] + x1, comp["y"] + h - y2,
                comp["x"] + x2, comp["y"] + h - y1)
    if o == "FN":
        return (comp["x"] + w - x2, comp["y"] + y1,
                comp["x"] + w - x1, comp["y"] + y2)
    raise ValueError(f"unsupported orientation {o} on {comp['name']}")


def overlap(a, b):
    eps = 1e-6
    return max(a[0], b[0]) < min(a[2], b[2]) - eps and max(a[1], b[1]) < min(a[3], b[3]) - eps


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--def", dest="def_file", required=True)
    ap.add_argument("--lef", required=True)
    ap.add_argument("--tech-lef", required=True)
    args = ap.parse_args()

    text = Path(args.def_file).read_text()
    rows = pc.parse_rows(text)
    if not rows:
        raise SystemExit("FAIL: no ROWs")
    macros = parse_lef(args.lef)
    comps = parse_components(text)
    if not comps:
        print("PDN_SIGNAL_INTEGRITY FAIL")
        print(" no placed components found; cannot validate PG pins")
        return 1
    shapes = pc.parse_special_shapes(text)
    pdn = [s for s in shapes if s["net"] in ("VDD", "GND") and s["layer"] in ("M1", "M2")]

    errors = {"electrical_short": [], "routing_obstruction": [],
              "pg_pg_short": [], "pg_pin_unconnected": []}

    for i, a in enumerate(pdn):
        for b in pdn[i + 1:]:
            if a["layer"] == b["layer"] and a["net"] != b["net"]:
                if overlap((a["x1"], a["y1"], a["x2"], a["y2"]),
                           (b["x1"], b["y1"], b["x2"], b["y2"])):
                    errors["pg_pg_short"].append(f"{a['net']} vs {b['net']} on {a['layer']}")

    for comp in comps:
        cell = macros.get(comp["cell"])
        if cell is None:
            errors["pg_pin_unconnected"].append(f"{comp['name']}: cell {comp['cell']} not in LEF")
            continue
        for ctx, layer, rect in cell["rects"]:
            box = transform(rect, comp, cell)
            for s in pdn:
                if s["layer"] != layer:
                    continue
                sbox = (s["x1"], s["y1"], s["x2"], s["y2"])
                if not overlap(box, sbox):
                    continue
                if ctx in ("VDD", "GND"):
                    if ctx != s["net"]:
                        errors["pg_pg_short"].append(
                            f"{comp['name']}/{ctx} overlaps {s['net']} on {layer}"
                        )
                elif ctx == "OBS":
                    if not comp["cell"].startswith("FILL"):
                        errors["routing_obstruction"].append(
                            f"{comp['name']}/{ctx} on {layer} overlaps {s['net']} PDN"
                        )
                else:
                    errors["electrical_short"].append(
                        f"{comp['name']}/{ctx} signal on {layer} overlaps {s['net']} PDN"
                    )

    for comp in comps:
        cell = macros.get(comp["cell"])
        if cell is None:
            continue
        for pin_net in ("VDD", "GND"):
            pin_rects = [r for ctx, layer, r in cell["rects"] if ctx == pin_net and layer == "M1"]
            if not pin_rects:
                continue
            covered = False
            for rect in pin_rects:
                box = transform(rect, comp, cell)
                if any(
                    s["net"] == pin_net and s["layer"] == "M1" and s["width"] > 0
                    and overlap(box, (s["x1"], s["y1"], s["x2"], s["y2"]))
                    for s in pdn
                ):
                    covered = True
                    break
            if not covered:
                errors["pg_pin_unconnected"].append(
                    f"{comp['name']}/{pin_net} has no M1 PDN coverage"
                )

    total = sum(len(v) for v in errors.values())
    if total:
        print("PDN_SIGNAL_INTEGRITY FAIL")
        for kind, items in errors.items():
            for item in items:
                print(f" {kind}: {item}")
        return 1

    print("PDN_SIGNAL_INTEGRITY PASS")
    print(f" components={len(comps)} pdn_shapes={len(pdn)} rows={len(rows)}")
    print(" electrical_short=0 routing_obstruction=0 pg_pg_short=0 pg_pin_unconnected=0")
    return 0


if __name__ == "__main__":
    sys.exit(main())
