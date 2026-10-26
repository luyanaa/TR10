#!/usr/bin/env python3
"""Assert the exact TR10 PDN experiment geometry from a DEF file."""

import argparse
import re
import sys
from pathlib import Path

UNITS = 1000
RAIL_W = 3.4


def parse_rows(text):
    rows = []
    for line in text.splitlines():
        m = re.match(r"\s*ROW\s+(\S+)\s+(\S+)\s+(-?\d+)\s+(-?\d+)\s+(\S+)", line)
        if m:
            rows.append({
                "name": m.group(1),
                "x": int(m.group(3)) / UNITS,
                "y": int(m.group(4)) / UNITS,
                "orient": m.group(5),
            })
    return rows


def parse_site_height(tech_lef):
    text = Path(tech_lef).read_text()
    m = re.search(r"(?m)^SITE\s+\S+\s*\n\s*CLASS\s+CORE\s*;\s*\n\s*SIZE\s+[\d.]+\s+BY\s+([\d.]+)", text)
    if not m:
        raise SystemExit(f"could not parse SITE height from {tech_lef}")
    return float(m.group(1))


def parse_special_shapes(text):
    shapes = []
    inside = False
    net = None
    for line in text.splitlines():
        s = line.strip()
        if s.startswith("SPECIALNETS"):
            inside = True
            continue
        if s == "END SPECIALNETS":
            break
        if not inside:
            continue
        m = re.match(r"-\s+(\S+)\s+", s)
        if m:
            net = m.group(1)
            continue
        body = re.sub(r"^\+\s*", "", s)
        m = re.match(
            r"(ROUTED|NEW)\s+(M1|M2)\s+(\d+)\s+\+\s+SHAPE\s+STRIPE\s+"
            r"\(\s*(-?\d+)\s+(-?\d+)\s*\)(?:\s+\(\s*(-?\d+)\s+(-?\d+)\s*\))?"
            r"(?:\s+(\S+))?",
            body,
        )
        if not m or net is None:
            continue
        layer = m.group(2)
        width = int(m.group(3)) / UNITS
        x1 = int(m.group(4)) / UNITS
        y1 = int(m.group(5)) / UNITS
        x2 = int(m.group(6)) / UNITS if m.group(6) is not None else x1
        y2 = int(m.group(7)) / UNITS if m.group(7) is not None else y1
        via = m.group(8)
        if layer == "M1" and width > 0:
            y1 -= width / 2.0
            y2 += width / 2.0
        elif layer == "M2" and width > 0:
            x1 -= width / 2.0
            x2 += width / 2.0
        shapes.append({
            "net": net, "layer": layer, "width": width,
            "x1": min(x1, x2), "x2": max(x1, x2),
            "y1": min(y1, y2), "y2": max(y1, y2),
            "via": via,
        })
    return shapes


def merge_intervals(intervals):
    merged = []
    for s, e in sorted(intervals):
        if not merged:
            merged.append([s, e])
        elif s <= merged[-1][1] + 1e-6:
            merged[-1][1] = max(merged[-1][1], e)
        else:
            merged.append([s, e])
    return merged


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--def", dest="def_file", required=True)
    ap.add_argument("--tech-lef", required=True)
    args = ap.parse_args()

    text = Path(args.def_file).read_text()
    rows = parse_rows(text)
    if not rows:
        raise SystemExit("FAIL: no ROWs in DEF")
    row_h = parse_site_height(args.tech_lef)
    shapes = parse_special_shapes(text)

    m1 = [s for s in shapes if s["layer"] == "M1" and s["width"] > 0]
    m2 = [s for s in shapes if s["layer"] == "M2" and s["width"] > 0]
    vias = [s for s in shapes if s["via"] and s["via"].startswith("M1M2_V1")]
    errors = []

    intervals = {"GND": [], "VDD": []}
    for row in rows:
        if row["orient"] == "N":
            intervals["GND"].append((row["y"] + 1.7 - 1.7, row["y"] + 1.7 + 1.7))
            intervals["VDD"].append((row["y"] + 55.9 - 1.7, row["y"] + 55.9 + 1.7))
        elif row["orient"] == "FS":
            intervals["GND"].append((row["y"] + row_h - 1.7 - 1.7, row["y"] + row_h - 1.7 + 1.7))
            intervals["VDD"].append((row["y"] + row_h - 55.9 - 1.7, row["y"] + row_h - 55.9 + 1.7))
        else:
            errors.append(f"unsupported row orientation {row['orient']}")

    expected = {net: merge_intervals(ivs) for net, ivs in intervals.items()}

    def find_center(layer_shapes, net, axis, value):
        for s in layer_shapes:
            cy = (s["y1"] + s["y2"]) / 2.0
            cx = (s["x1"] + s["x2"]) / 2.0
            if s["net"] == net and abs((cy if axis == "y" else cx) - value) < 1e-6:
                return s
        return None

    for net, ivs in expected.items():
        for s, e in ivs:
            center = (s + e) / 2.0
            shape = find_center(m1, net, "y", center)
            if shape is None:
                errors.append(f"missing M1 {net} center y={center}")
            elif abs((shape["y2"] - shape["y1"]) - (e - s)) > 1e-6:
                errors.append(f"M1 {net} y={center}: width {shape['y2']-shape['y1']} != {e-s}")

    # The MX segment must be covered exactly; if it is merged with the next
    # same-net row rail, the merged stripe may extend above it.
    for row in rows:
        if row["orient"] != "FS":
            continue
        want_y1 = row["y"] + row_h - 3.4
        want_y2 = row["y"] + row_h
        if not any(
            s["net"] == "GND" and s["layer"] == "M1"
            and s["y1"] <= want_y1 + 1e-6 and s["y2"] >= want_y2 - 1e-6
            for s in m1
        ):
            errors.append(f"MX GND segment [{want_y1},{want_y2}] is not covered")

    # The M1 rails span the core width; use their extent as the core x bounds.
    # DIEAREA may be wider than CORE, so it is only a fallback.
    if m1:
        xmin = min(s["x1"] for s in m1)
        xmax = max(s["x2"] for s in m1)
    else:
        errors.append("no M1 shapes; cannot derive core x bounds")
        xmin = xmax = 0.0
    expected_m2 = {"VDD": xmin + RAIL_W / 2.0, "GND": xmax - 2.0 * RAIL_W}
    for net, x in expected_m2.items():
        shape = find_center(m2, net, "x", x)
        if shape is None:
            errors.append(f"missing M2 {net} center x={x}")
        elif abs((shape["x2"] - shape["x1"]) - RAIL_W) > 1e-6:
            errors.append(f"M2 {net} x={x}: width {shape[x2]-shape[x1]} != {RAIL_W}")
    for net, ivs in expected.items():
        for s, e in ivs:
            y = (s + e) / 2.0
            x = xmin + RAIL_W / 2.0 if net == "VDD" else xmax - 2.0 * RAIL_W
            if not any(
                v["net"] == net
                and abs((v["x1"] + v["x2"]) / 2.0 - x) < 1e-6
                and abs((v["y1"] + v["y2"]) / 2.0 - y) < 1e-6
                for v in vias
            ):
                errors.append(f"missing M1M2_V1 for {net} at ({x},{y})")
    if errors:
        print("PDN_POSTCHECK FAIL")
        for e in errors:
            print(" -", e)
        return 1

    print("PDN_POSTCHECK PASS")
    print(f" rows={len(rows)} row_height={row_h}")
    print(f" M1 intervals: {expected}")
    print(f" M2 centers: VDD={xmin + RAIL_W / 2.0}, GND={xmax - 2.0 * RAIL_W}")
    print(f" V1 count: {len(vias)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
