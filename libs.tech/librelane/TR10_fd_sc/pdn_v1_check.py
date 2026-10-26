#!/usr/bin/env python3
"""Arithmetic V1 landing check for the TR10 PDN experiment.

Assumes the current TR-1um/TR10 rules used in this experiment:
  V1 cut = 1.4 um, M1 enclosure = 1.0 um, M2 enclosure = 1.0 um.
It checks that each generated M1M2_V1 center has M1 and M2 coverage of at
least [center-1.7, center+1.7] on both axes.  It does not replace the full
GC/CO/M2-spacing DRC.
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import pdn_experiment_postcheck as pc

ENC = 1.7  # 1.4 cut / 2 + 1.0 enclosure


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--def", dest="def_file", required=True)
    args = ap.parse_args()
    text = Path(args.def_file).read_text()
    shapes = pc.parse_special_shapes(text)
    vias = [s for s in shapes if s["via"] and s["via"].startswith("M1M2_V1")]
    m1 = [s for s in shapes if s["layer"] == "M1" and s["width"] > 0]
    m2 = [s for s in shapes if s["layer"] == "M2" and s["width"] > 0]

    errors = []
    for v in vias:
        x = (v["x1"] + v["x2"]) / 2.0
        y = (v["y1"] + v["y2"]) / 2.0
        for layer, layer_shapes in (("M1", m1), ("M2", m2)):
            ok = False
            for s in layer_shapes:
                if s["net"] != v["net"]:
                    continue
                if (s["x1"] <= x - ENC + 1e-6 and s["x2"] >= x + ENC - 1e-6
                        and s["y1"] <= y - ENC + 1e-6 and s["y2"] >= y + ENC - 1e-6):
                    ok = True
                    break
            if not ok:
                errors.append(f"{v['via']} {v['net']} at ({x},{y}) lacks {layer} 1.0 um enclosure")

    if errors:
        print("PDN_V1_CHECK FAIL")
        for e in errors:
            print(" -", e)
        return 1
    print("PDN_V1_CHECK PASS")
    print(f" vias={len(vias)} M1/M2 enclosure>=1.0 um for all checked vias")
    print(" NOTE: GC/CO spacing and final mask DRC are still required.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
