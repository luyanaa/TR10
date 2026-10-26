#!/usr/bin/env python3
"""Gate a KLayout DRC report for the TR10 PDN experiment.

The synthetic top cell has no substrate/text annotation, so the library
GC.ANT floating-gate check is expected.  Any V1/M1/M2/CO violation is fatal
for this PDN experiment.
"""

import argparse
import re
import sys
from pathlib import Path


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--report", required=True)
    args = ap.parse_args()
    text = Path(args.report).read_text(errors="replace")
    items = re.findall(r"<item>.*?</item>", text, re.S)
    bad = []
    allowed = 0
    for item in items:
        m = re.search(r"<category>(.*?)</category>", item, re.S)
        cat = m.group(1) if m else "?"
        if "GC.ANT" in cat:
            allowed += 1
            continue
        if re.search(r"(^|[:'])\\s*(V1|M1|M2|CO)\\.", cat) or re.search(r"^'(V1|M1|M2|CO)\\.", cat):
            bad.append(cat)
        else:
            # Unknown categories are reported, not silently accepted.
            bad.append(f"unexpected category: {cat}")

    if bad:
        print("PDN_DRC_GATE FAIL")
        for b in bad:
            print(" -", b)
        return 1
    print("PDN_DRC_GATE PASS")
    print(f" items={len(items)} allowed_GC_ANT={allowed} V1/M1/M2/CO=0")
    return 0


if __name__ == "__main__":
    sys.exit(main())
